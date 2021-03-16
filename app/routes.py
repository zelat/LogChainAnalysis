from flask import Flask, render_template, request, jsonify
from app import app
import json
from utils import esData
import time


@app.route('/', methods=("GET", "POST"))
def index():
    if request.method == 'GET':
        return render_template('index.html')
    if request.method == "POST":
        log_info = request.form.to_dict()
        uuid = log_info.get("uuid")
        vip = log_info.get("vip")
        date = log_info.get("date").replace("-", ".")
    # else:
    #     uuid = "3e6c2689-ccea-4028-b495-ef2a18e6101b"
    #     vip = "172.118.32.30"
    #     date = "2021.03.16"
        resource_index = "resource-log-" + date
        obj = esData.ElasticObj("_doc")
        index_List = list(obj.indices.get_alias('*-log-' + date).keys())
        index_List.remove(resource_index)
        mappingDict = obj.getMappingByResource(resource_index, index_List, uuid, vip, date, 10)
        response = json.dumps(mappingDict, sort_keys=True, indent=4, separators=(',', ': '))
    return render_template("showlog.html", response=response)

@app.route('/detailLog', methods=['POST'])
def detailLog():
    obj = esData.ElasticObj("_doc")
    data = request.get_json()
    index = data['index']
    request_id = data['request_id']
    jsonData = json.dumps(obj.getLog(index_name=index, request_id=request_id))
    return  jsonify(jsonData)


