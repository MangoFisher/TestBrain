from django.conf import settings


def get_agent_llm_configs(agent_name: str):
    """
    获取AI Agent的LLM配置
    """
    llm_config = getattr(settings, "LLM_PROVIDERS", {})
    # global_default_provider是全局默认的LLM提供商, 如果AI Agent没有配置LLM提供商, 则使用这个默认提供商
    global_default_provider = llm_config.get("default_provider", "deepseek")
    global_providers = {k: v for k, v in llm_config.items() if k != "default_provider"}

    agent_defaults = getattr(settings, "AGENT_LLM_DEFAULTS", {})
    # agent_provider_config是settings.py中的AGENT_LLM_DEFAULTS中的配置, 即每个AI Agent的默认LLM提供商
    agent_provider = agent_defaults.get(agent_name).get("provider", global_default_provider)

    return agent_provider, global_providers

