# nvidianemoguardrails-microsoftfoundry-otel-grafana-dockercompose
Scripts do Docker Compose para subida de um ambiente de testes do NVIDIA NeMo Guardrails com capacidade de AI Gateway. Inclui monitoramento/geração de traces Tempo + Alloy (OpenTelemetry) + Grafana (dashboard), com implementação de guardrails evitando menções a termos políticos. IA testada: Microsoft Foundry.


Saiba mais sobre o projeto open source NVIDIA NeMo Guardrails em: **https://github.com/NVIDIA-NeMo/Guardrails**

## Testes

Para os testes aqui descritos foram configurados guardrails a fim de evitar menções a termos políticos.

Envio de uma requisição de uma requisição inválida via REST Client no Visual Studio Code:

![Requisição inválida no VS Code](img/01-req-invalida.png)

Envio de uma requisição válida utilizando novamente REST Client + VS Code:

![Requisição válida no VS Code](img/02-req-valida.png)

Testes via chat disponibilizado pelo Nemo Guardrails:

![Testes com o chat do Nemo Guardrails](img/03-chat.png)

Traces exportados para o Jaeger:

![Traces no Jaeger](img/04-traces-gerados.png)

Um trace em detalhes na interface na interface do Jaeger:

![Detalhes de um trace no Jaeger](img/05-exemplo-trace.png)