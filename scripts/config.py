"""项目配置：Seedream 模型与 TOS 上传。"""

# Seedream / Ark 图像生成
SEEDREAM_MODEL = "doubao-seedream-5-0-260128"
ARK_IMAGES_GENERATIONS_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

# TOS 对象存储（upload_file）
TOS_ENDPOINT = "tos-cn-beijing.volces.com"
TOS_REGION = "cn-beijing"
TOS_BUCKET = "auto-image"

# 需要设置环境变量
# ARK_DOUBAO_SEEDREAM_API_KEY
# TOS_ACCESS_KEY
# TOS_SECRET_KEY