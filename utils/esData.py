from elasticsearch import Elasticsearch
import re
import json

class ElasticObj:
    def __init__(self, index_type, host="10.192.31.160"):
        self.index_type = index_type
        self.size = 500
        self.es = Elasticsearch([host], port=9200, timeout=200)
        self.indices = self.es.indices

    def getReqID(self, logmessage):
        pattern = "req-[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}"
        Req_ID = re.findall(pattern, logmessage)
        Req_ID = list(set(Req_ID))
        return Req_ID

    # 查询resource里的request_id
    # 1. 过滤掉200响应
    #         201-206都表示服务器成功处理了请求的状态代码，说明网页可以正常访问。
    #         200（成功）  服务器已成功处理了请求。通常，这表示服务器提供了请求的网页。
    #         201（已创建）  请求成功且服务器已创建了新的资源。
    #         202（已接受）  服务器已接受了请求，但尚未对其进行处理。
    #         203（非授权信息）  服务器已成功处理了请求，但返回了可能来自另一来源的信息。
    #         204（无内容）  服务器成功处理了请求，但未返回任何内容。
    #         205（重置内容） 服务器成功处理了请求，但未返回任何内容。与 204 响应不同，此响应要求请求者重置文档视图（例如清除表单内容以输入新内容）。
    #         206（部分内容）  服务器成功处理了部分 GET 请求。
    def getReqIDFromResource(self, index_name, uuid, size):
        request_id_list = []
        doc = {
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                },
                {
                    "@timestamp": {
                        "order": "desc",
                        "unmapped_type": "boolean"
                    }
                }
            ],
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "match_all": {}
                        },
                        {
                            "bool": {
                                "minimum_should_match": 1,
                                "should": [
                                    {
                                        "match_phrase": {
                                            "logmessage": "Client in-bound"
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "match_phrase": {
                                "uuid": uuid
                            }
                        }
                    ],
                    "should": [],
                    "must_not": [
                        {
                            "match_phrase": {
                                "logmessage": "< 200"
                            }
                        }
                    ]
                }
            }
        }
        try:
            _searched = self.es.search(index=index_name, doc_type=self.index_type, body=doc)
            for hit in _searched['hits']['hits']:
                request_id_list.append(self.getReqID(hit['_source']['logmessage'])[0])
            return request_id_list
        except Exception as e:
            raise e

    def getReqIDFromNovaCompute(self, index_name, request_id, indexList, size):
        dict = {}
        doc = {
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                },
                {
                    "@timestamp": {
                        "order": "desc",
                        "unmapped_type": "boolean"
                    }
                }
            ],
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "match_all": {}
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match_phrase": {
                                            "logmessage": "x-openstack-request-id"
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            }
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match_phrase": {
                                            "logmessage": "RESP BODY"
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            }
                        },
                        {
                            "match_phrase": {
                                "request_id": request_id
                            }
                        }
                    ],
                    "should": [],
                    "must_not": []
                }
            }
        }
        try:
            _searched = self.es.search(index=index_name, doc_type=self.index_type, body=doc)
            for hit in _searched['hits']['hits']:
                list = []
                req_id = self.getReqID(hit['_source']['logmessage'])[0]
                for index in indexList:
                    if self.isREQIDExist(index, req_id, self.size) == True:
                        list.append(index)
                dict[req_id] = list
            return dict
        except Exception as e:
            raise e

    def isREQIDExist(self, index_name, request_id, size):
        doc = {
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                },
                {
                    "@timestamp": {
                        "order": "desc",
                        "unmapped_type": "boolean"
                    }
                }
            ],
            "stored_fields": [
                "*"
            ],
            "script_fields": {},
            "docvalue_fields": [
                {
                    "field": "@timestamp",
                    "format": "date_time"
                }
            ],
            "_source": {
                "excludes": []
            },
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "match_all": {}
                        },
                        {
                            "match_phrase": {
                                "request_id": request_id
                            }
                        }
                    ],
                    "should": [],
                    "must_not": []
                }
            }
        }
        try:
            _searched = self.es.search(index=index_name, doc_type=self.index_type, body=doc)
            for hit in _searched['hits']['hits']:
                if request_id == self.getReqID(hit['_source']['request_id'])[0]:
                    return True
                    break
        except Exception as e:
            raise e

    # Resource日志中取得的resourceId与openstack的匹配关系
    def getMappingByResource(self, resourceIndex, indexList, uuid, date, size):
        # while True:
        try:
            resource_req_id_list = self.getReqIDFromResource(resourceIndex, uuid, size)
            dict = {}
            for req_id in resource_req_id_list:
                newList = []
                filterList = []
                for index in indexList:
                    if self.isREQIDExist(index, req_id, self.size) == True:
                        filterList.append(index)
                        if index == "nova-compute-log-" + date:
                            # print('nova-compute: ',
                            #       self.getReqIDFromNovaCompute("nova-compute-log-" + date, req_id, indexList, 10))
                            indexDict = {}
                            novaComputeDict = self.getReqIDFromNovaCompute("nova-compute-log-" + date, req_id,
                                                                           indexList, 10)
                            indexDict[index] = novaComputeDict
                            if len(novaComputeDict) > 0:
                                newList.append(indexDict)
                            newList.append(index)
                        else:
                            newList.append(index)
                if len(newList) > 1:
                    dict[req_id] = newList
                else:
                    dict[req_id] = filterList
            return dict
        except Exception as e:
            print('Error', e)

    #查询index, requestId
    def getLog(self, index_name, request_id):
        logDict = {}
        i = 1
        doc = {
            "size": self.size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                },
                {
                    "@timestamp": {
                        "order": "desc",
                        "unmapped_type": "boolean"
                    }
                }
            ],
            "stored_fields": [
                "*"
            ],
            "script_fields": {},
            "docvalue_fields": [
                {
                    "field": "@timestamp",
                    "format": "date_time"
                }
            ],
            "_source": {
                "excludes": []
            },
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "match_all": {}
                        },
                        {
                            "match_phrase": {
                                "request_id": request_id
                            }
                        }
                    ],
                    "should": [],
                    "must_not": []
                }
            }
        }
        try:
            _searched = self.es.search(index=index_name, doc_type=self.index_type, body=doc)
            for hit in _searched['hits']['hits']:
                dict = {}
                dict['@timestamp'] = hit['_source']['@timestamp']
                dict['level'] = hit['_source']['level']
                dict['request_id'] = hit['_source']['request_id']
                dict['project_id'] = hit['_source']['project_id']
                dict['user_id'] = hit['_source']['user_id']
                dict['logmessage'] = hit['_source']['logmessage']
                logDict[i] = dict
                i += 1
            return logDict
        except Exception as e:
            raise e

