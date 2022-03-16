import importlib

def import_settings(module_name, globals_dict):
    try:
        module_settings = importlib.import_module(module_name)
        for item in dir(module_settings):
            globals_dict[item] = getattr(module_settings, item)
    except Exception as e:
        print(str(e))
        print("error importing {} module settings")