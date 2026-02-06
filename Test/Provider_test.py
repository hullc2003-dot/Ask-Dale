from provider_cfg.provider_layer import ProviderLayer
from provider_cfg.config import ProviderConfig
from provider_cfg.provider_usage import load_usage

def run_test():
    config = ProviderConfig()
    usage = load_usage()

    layer = ProviderLayer(config, usage)

    model = config.default_model
    prompt = "Say hello to Dale"

    print("Using model:", model)
    response = layer.call_model(model, prompt)
    print("Response:", response)

if __name__ == "__main__":
    run_test()
