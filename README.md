# Relatório para Análise de Performance de Pods (Prefect/Grafana)

Este repositório contém ferramentas de automação para análise de logs de consumo de recursos (CPU e Memória) de Pods Kubernetes, com foco especial em serviços orquestrados pelo **Prefect**.

O objetivo é identificar **anomalias**, **gargalos de infraestrutura** e **padrões de instabilidade ("burst")**, gerando relatórios técnicos automáticos para orientar ações de otimização pelos desenvolvedores.

-----

## Funcionalidades

  * **Detecção de Saturação:** Calcula automaticamente a porcentagem de uso do cluster vs. capacidade total.
  * **Análise de "Burst":** Identifica serviços instáveis (onde o pico de CPU é muito superior à média), típicos de workers de ETL.
  * **Métricas Estatísticas:** Calcula Média, Pico e P95 (Percentil 95) para Memória e CPU.
  * **Relatório Visual:** Gera gráficos de timeline e ranking de ofensores.
  * **Modo Confidencial:** Inclui script para anonimizar dados sensíveis antes de compartilhamento.

## Estrutura do Projeto

  * `gerar_relatorio.py`: Script principal. Lê os CSVs e gera o relatório Markdown + Imagens.


## Pré-requisitos

  * Python 3.8+
  * Bibliotecas Python (instale via pip):
    ```bash
    pip install pandas matplotlib numpy
    ```

## Como extrair os dados do Grafana

Para que o script funcione, é necessário exportar os dados:

1.  Acesse o Dashboard do Grafana referente ao Cluster/Namespace desejado.
2.  Vá no painel de **CPU Usage** -\> Clique no título -\> **Inspect** -\> **Data**.
3.  Em "Data Options", selecione **"Series joined by time"** (Muito importante\!).
4.  Clique em **Download CSV**.
5.  Repita o processo para o painel de **Memory Usage**.
6.  Salve os arquivos na raiz deste projeto.

## usage  Como usar

### 1\. Gerar Relatório Técnico

Edite o arquivo `gerar_relatorio.py` e certifique-se de que os nomes dos arquivos CSV correspondem aos que você baixou.

```bash
python gerar_relatorio.py
```

> O relatório será gerado na pasta `relatorio_performance/` contendo um arquivo `RELATORIO_TECNICO.md` e os gráficos.


-----

## Interpretando os Resultados

O relatório destaca três métricas principais que exigem ação dos desenvolvedores:

### 1\. Saturação Global (Risco de Infra)

  * **🔴 Crítico (\>80% CPU):** O nó está perto de travar. É necessário aumentar recursos (Scale Up) ou otimizar queries.
  * **🔴 Crítico (\>90% Memória):** Risco iminente de *OOMKilled* (Pods sendo mortos pelo sistema).

### 2\. Burst Ratio (Instabilidade)

Mede quantas vezes o **Pico** é maior que a **Média**.

  * **Exemplo:** Um worker do Prefect que roda ocioso (0.1 core) e explode para 2.0 cores tem um Burst Ratio de **20x**.
  * **Ação:** Se muitos pods tiverem Burst alto, eles podem estar competindo por CPU no mesmo instante, causando lentidão geral. Recomenda-se isolar esses workers ou ajustar `limits`.

### 3\. Memory Bloat (Vazamento)

  * **Padrão:** Memória que sobe constantemente e nunca desce, ou consumo base muito alto (\> 2GiB) para microsserviços simples.
  * **Ação:** Investigar código Python (DataFrames carregados inteiros na RAM) ou configurações de JVM.

-----

## 🤝 Contribuição

1.  Faça um Fork do projeto
2.  Crie sua Feature Branch (`git checkout -b feature/NovaAnalise`)
3.  Commit suas mudanças (`git commit -m 'Add new metric'`)
4.  Push para a Branch (`git push origin feature/NovaAnalise`)
5.  Abra um Pull Request

-----

**Mantido por Patrícia Carbri**