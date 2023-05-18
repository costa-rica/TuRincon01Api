import os
import json
from dotenv import load_dotenv

load_dotenv()


with open(os.path.join(os.environ.get('CONFIG_PATH'), os.environ.get('CONFIG_FILE_NAME'))) as config_file:
    config_dict = json.load(config_file)


class ConfigBase:

    def __init__(self):

        self.SECRET_KEY = config_dict.get('SECRET_KEY')
        # self.WEB_ROOT = os.environ.get('WEB_ROOT')
        self.API_ROOT = os.environ.get('API_ROOT')
        self.DB_ROOT = os.environ.get('DB_ROOT')
        self.DESTINATION_PASSWORD = config_dict.get('DESTINATION_PASSWORD')


class ConfigLocal(ConfigBase):

    def __init__(self):
        super().__init__()

    DEBUG = True
            

class ConfigDev(ConfigBase):

    def __init__(self):
        super().__init__()

    DEBUG = True
            

class ConfigProd(ConfigBase):

    def __init__(self):
        super().__init__()

    DEBUG = False


if os.environ.get('CONFIG_TYPE')=='local':
    config = ConfigLocal()
    print('- /app_pacakge/config: Local')
elif os.environ.get('CONFIG_TYPE')=='dev':
    config = ConfigDev()
    print('- /app_pacakge/config: Development')
elif os.environ.get('CONFIG_TYPE')=='prod':
    config = ConfigProd()
    print('- /app_pacakge/config: Production')