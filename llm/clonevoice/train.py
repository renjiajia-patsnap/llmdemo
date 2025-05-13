import json
import time
import requests
import hashlib
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
from dotenv import load_dotenv

load_dotenv()
# 获取鉴权token
def getAuthorization(appId, apikey,timeStamp,data):
    # timeStamp = int(time.time() * 1000)
    # data = '{"base":{"appid":"' + appId + '","version":"v1","timestamp":"' + str(timeStamp) + '"},"model":"remote"}'
    body = json.dumps(data)
    keySign = hashlib.md5((apikey + str(timeStamp)).encode('utf-8')).hexdigest()
    print(body)
    sign = hashlib.md5((keySign + body).encode("utf-8")).hexdigest()
    return sign
#获取鉴权token
def getToken(appid,apikey):
    #构建请求头headers
    timeStamp = int(time.time() * 1000)
    body = {"base":{"appid": appid ,"version":"v1","timestamp": str(timeStamp)},"model":"remote"}
    headers = {}
    headers['Authorization'] = getAuthorization(appid,apikey,timeStamp,body)
    headers['Content-Type'] = 'application/json'
    print("body------>",body)
    print("headers----->",headers)
    response = requests.post(url='http://avatar-hci.xfyousheng.com/aiauth/v1/token', data= json.dumps(body),headers= headers).text
    resp = json.loads(response)
    print("resp---->",resp)
    if ('000000' == resp['retcode']):
        return resp['accesstoken']


class VoiceTrain(object):
    def __init__(self,appid,apikey):
        # self.sign = ''
        self.appid = appid
        self.apikey = apikey
        self.token = getToken(appid,apikey)
        self.time = int(time.time()* 1000)
        self.taskId = ''

    def getSign(self,body):
        keySign = hashlib.md5((str(body)).encode('utf-8')).hexdigest()
        sign = hashlib.md5((self.apikey+ str(self.time) + keySign).encode("utf-8")).hexdigest()
        return sign

    def getheader(self,sign):
        return {"X-Sign":sign,"X-Token":self.token,"X-AppId":self.appid,"X-Time":str(self.time)}

    #支持获取训练文本列表
    def getText(self):
        textid = 5001  #通用的训练文本集
        body = {"textId":textid}
        sign = self.getSign(body)
        headers =self.getheader(sign)

        response = requests.post(url ='http://opentrain.xfyousheng.com/voice_train/task/traintext',json= body,headers=headers).json()
        print(response)
        print("请使用以下官方文本录音，然后进行训练：")
        textlist= response['data']['textSegs']
        for line in textlist:
            print(line['segId'])
            print(line['segText'])

    #创建训练任务
    def createTask(self):
        body={
            "taskName":"test23",  #任务名称，可自定义
            "sex" :1 ,  # 训练音色性别   1：男     2 ：女
            "resourceType":12,
            "resourceName" :"创建音库test1",  #音库名称，可自定义
            "language":"cn",   # 不传language参数，默认中文；英：en、日：jp、韩：ko、俄：ru
            # "callbackUrl":"https://XXXX/../"   #任务结果回调地址
        }
        sign = self.getSign(body)
        headers = self.getheader(sign)
        response = requests.post(url ='http://opentrain.xfyousheng.com/voice_train/task/add',json= body,headers=headers).text
        print(response)
        resp = json.loads(response)
        print("创建任务：",resp)
        return resp['data']

    #添加音频到训练任务（上传音频url）
    ##音频要求：
    # 1、音频格式限制wav、mp3、m4a、pcm，推荐使用无压缩wav格式
    # 2、单通道，采样率24k及以上，位深度16bit，时长无严格限制，音频大小限制3M。音频大小限制3M
    def addAudio(self,audiourl,textId,textSegId):
        self.taskId =self.createTask()
        body ={
            "taskId":self.taskId,
            "audioUrl": audiourl,  #wav格式音频的存储对象地址，需保证地址可直接下载
            "textId": textId,   #通用训练文本集
            "textSegId": textSegId     #这里demo 演示用固定文本训练，应用层可以让用户从 getText返回的列表中选择
        }
        sign = self.getSign(body)
        headers = self.getheader(sign)
        response = requests.post(url='http://opentrain.xfyousheng.com/voice_train/audio/v1/add', json=body, headers=headers).text
        print(response)

    # 添加音频到训练任务（上传本地音频文件）
    ##音频要求：
    # 1、音频格式限制wav、mp3、m4a、pcm，推荐使用无压缩wav格式
    # 2、单通道，采样率24k及以上，位深度16bit，时长无严格限制，音频大小限制3M。音频大小限制3M
    def addAudiofromPC(self,  textId, textSegId,path):
        url = 'http://opentrain.xfyousheng.com/voice_train/task/submitWithAudio'
        self.taskId = self.createTask()
        # body = {
        #     "taskId": self.taskId,
        #     "audioUrl": audiourl,  # wav格式音频的存储对象地址，需保证地址可直接下载
        #     "textId": textId,  # 通用训练文本集
        #     "textSegId": textSegId  # 这里demo 演示用固定文本训练，应用层可以让用户从 getText返回的列表中选择
        # }
        # 构造body体
        formData = MultipartEncoder(
            fields={
                "file": (path, open(path, 'rb'), 'audio/wav'),  # 如果需要上传本地音频文件，可以将文件路径通过path 传入
                "taskId": str(self.taskId),
                "textId": str(textId),  # 通用训练文本集
                "textSegId": str(textSegId)  # 这里demo 演示用固定文本训练，应用层可以让用户从 getText返回的列表中选择
            }
        )
        print(formData)

        sign = self.getSign(formData)
        headers = self.getheader(sign)
        headers['Content-Type'] = formData.content_type
        response = requests.post(url=url, data= formData,headers=headers).text
        print(response)


    def submitTask(self):
        body ={"taskId" :self.taskId}
        sign = self.getSign(body)
        headers = self.getheader(sign)
        response = requests.post(url='http://opentrain.xfyousheng.com/voice_train/task/submit', json=body, headers=headers).text
        print(response)

    def getProcess(self):
        body = {"taskId": self.taskId}
        sign = self.getSign(body)
        headers = self.getheader(sign)
        response = requests.post(url='http://opentrain.xfyousheng.com/voice_train/task/result', json=body, headers=headers).text
        # resp = json.loads(response)
        return response




if  __name__ == '__main__':
    appid = os.getenv("APPID")
    apikey = os.getenv("APIKey")#在控制台获取

    voiceTrain = VoiceTrain(appid,apikey)

    # #获取训练文本列表，
    # 注：训练音色必须要使用官网提供的文本录音，并确保创建训练任务时 录音内容和指定的文本一致
    voiceTrain.getText()

    # 添加音频到训练任务中,通过对象存储的方式上传音频
    # audio = 'http://XXXXXX...XXX.wav'  #上传的 url 地址, 必须是 http|https 开头
    # voiceTrain.addAudio(audio,textId=5001,textSegId=14)  # textId,textSegId  请根据自己训练时选择的文本填写

    # 添加音频到训练任务中,通过上传本地音频文件的方式
    path = 'data/origin_audio.wav'
    voiceTrain.addAudiofromPC(textId=5001,textSegId=1,path=path)

    #提交训练任务
    voiceTrain.submitTask()
    #获取训练结果有两种方式： 1、Client被动回调，通过创建任务时设置callbackurl ; 2、Client主动轮询任务进度。
    #这里用方法2 实现
    while(1):
        response = voiceTrain.getProcess()
        resp = json.loads(response)
        # print(resp)
        status = resp['data']['trainStatus']
        if(-1 == status):
            print("还在训练中，请等待......")
        if(1 == status):
            print("训练成功，请用该音库开始进行语音合成：")
            print("音库id(res_id)：" + resp['data']['assetId'])
            break
        if(0 ==status):
            print("训练失败，训练时上传的音频必须要使用官方提供的文本录音，文本列表见：voiceTrain.getText() 方法执行结果")
            print(voiceTrain.taskId)
            break