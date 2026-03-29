# 说明

使用Seedream-5.0 API 生成高质量图片,需要生成图片时使用。适用于文生图、图生图以及生成关联组图的场景, 注意生成的图片是不带透明度的, 所以如果需要带透明度的图片, 需先生成某个纯色背景的内容图片,再使用rembg命令进一步处理

# 安装

cd {project_dir}/skills
git clone https://github.com/dzqdzq/gen_image
cd gen_image/script
uv pip install -r requirements.txt

# 配置
## TOS 对象存储, 修改config.py. 此目的上本地图片上传,然后图片URL交给模型处理
TOS_ENDPOINT = "tos-cn-beijing.volces.com"
TOS_REGION = "cn-beijing"
TOS_BUCKET = "auto-image"

## 需要设置环境变量
# ARK_DOUBAO_SEEDREAM_API_KEY
# TOS_ACCESS_KEY
# TOS_SECRET_KEY

## tos access token申请地址
https://console.volcengine.com/iam/keymanage

## seedream api key申请地址
https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey