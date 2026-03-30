-- Rename agent_tools_registry → agent_integrations
-- Matches tools.md §2 AgentIntegration naming

alter table agent_tools_registry rename to agent_integrations;

alter index idx_agent_tools_registry_agent rename to idx_agent_integrations_agent;

alter table agent_integrations
  rename constraint agent_tools_registry_agent_id_integration_id_key
  to agent_integrations_agent_id_integration_id_key;

alter table agent_integrations
  rename constraint agent_tools_registry_pkey
  to agent_integrations_pkey;
