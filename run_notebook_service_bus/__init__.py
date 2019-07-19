import azure.functions as func
from yaml import safe_load as load


def main(msg: func.ServiceBusMessage):

    try:
        params = load(
            msg.get_body().decode("utf-8")
        )
    except Exception as e:  
        raise Exception(str(e) + str(msg.get_body().decode("utf-8")))

    raise Exception (params)
