# LogChainAnalysis
用户一般通过云管平台或者API来向Openstack-API来申请资源调度，当云管平台向openstack发送一个HTTP请求后，
Openstack会在回复的响应里添加一个request-id，使用这个request-id我们可以在日志中追踪到openstack的服务调度过程。

具体文档可以看：https://cloud.tencent.com/developer/article/1803367
