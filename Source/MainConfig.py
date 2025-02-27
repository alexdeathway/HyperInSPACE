
import os
import collections
import json

class MainConfig:
    fileName = "main.config"
    settings = collections.OrderedDict()

    # Saves the cfg file
    @staticmethod
    def saveConfig(fileName):
        print("ConfigFile - Save Config")
        jsn = json.dumps(MainConfig.settings)
        fp = os.path.join("Config", fileName)

        with open(fp, 'w') as f:
            f.write(jsn)

    # Loads the cfg file
    @staticmethod
    def loadConfig(fileName, version):
        print("MainConfig - Load Config")
        configPath = os.path.join("Config", fileName)
        if os.path.isfile(configPath):
            text = ""
            with open(configPath, 'r') as f:
                text = f.read()
                MainConfig.settings = json.loads(text, object_pairs_hook=collections.OrderedDict)
        else:
            MainConfig.createDefaultConfig(fileName, version)

    # Generates the default configuration
    @staticmethod
    def createDefaultConfig(fileName, version):
        print("MainConfig - File not found..")
        print("MainConfig - Create Default Config")

        # MainConfig.settings["cfgFile"] = ""
        MainConfig.settings["cfgFile"] = fileName
        MainConfig.settings["version"] = version
        MainConfig.settings["inDir"] = './Data'
        MainConfig.settings["outDir"] = './Data'
        MainConfig.settings["metFile"] = ""
        MainConfig.settings["popQuery"] = 0