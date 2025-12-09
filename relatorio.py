import pandas as pd
import matplotlib.pyplot as plt
import os
import re
import numpy as np
from datetime import datetime

# --- CONFIGURAÇÃO ---

FILE_CPU = 'CPU_headers.csv'
FILE_MEM = 'MEM_headers.csv'

# Configuração de Saída
OUTPUT_DIR = "relatorio_performance"
OUTPUT_FILE = "RELATORIO_TECNICO.md"

# --- FUNÇÕES UTILITÁRIAS ---

def parse_memory_value(val):
    """Converte '1.2 GiB', '500 MiB' para float (MiB)."""
    if pd.isna(val): return 0.0
    val_str = str(val).strip()
    if not val_str: return 0.0
    
    match = re.match(r"([0-9.]+)\s*([A-Za-z]+)", val_str)
    if not match:
        try: return float(val_str)
        except: return 0.0
            
    number = float(match.group(1))
    unit = match.group(2)
    
    if unit == 'GiB': return number * 1024
    elif unit == 'MiB': return number
    elif unit == 'KiB': return number / 1024
    else: return number

def format_bytes(size_mib):
    """Formata float MiB para string (GiB/MiB)."""
    if size_mib >= 1024: return f"{size_mib/1024:.2f} GiB"
    return f"{size_mib:.0f} MiB"

# --- ANÁLISE ---

def analyze_data():
    print(f"Lendo arquivos: {FILE_CPU} e {FILE_MEM}...")
    
    # Criar diretório de saída
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        df_mem = pd.read_csv(file_mem_path if 'file_mem_path' in locals() else FILE_MEM)
        df_cpu = pd.read_csv(file_cpu_path if 'file_cpu_path' in locals() else FILE_CPU)
    except Exception as e:
        print(f"Erro ao ler arquivos (verifique se estão na mesma pasta): {e}")
        return None

    # Processar Memória
    cols_ignorar = ['Time', 'max capacity', 'quota - requests', 'quota - limits']
    cols_pods_mem = [c for c in df_mem.columns if c not in cols_ignorar]
    
    df_mem_clean = df_mem.copy()
    for col in cols_pods_mem:
        df_mem_clean[col] = df_mem[col].apply(parse_memory_value)
    
    df_mem_clean['Time'] = pd.to_datetime(df_mem_clean['Time'])
    df_mem_clean['Total_Usage'] = df_mem_clean[cols_pods_mem].sum(axis=1)

    # Capacidade Memória
    if 'max capacity' in df_mem.columns:
        cap_mem = df_mem['max capacity'].apply(parse_memory_value).median()
    else:
        cap_mem = df_mem_clean['Total_Usage'].max() * 1.2

    # Processar CPU
    cols_pods_cpu = [c for c in df_cpu.columns if c not in cols_ignorar]
    df_cpu_clean = df_cpu.copy()
    df_cpu_clean['Time'] = pd.to_datetime(df_cpu_clean['Time'])
    df_cpu_clean[cols_pods_cpu] = df_cpu_clean[cols_pods_cpu].fillna(0)
    df_cpu_clean['Total_Usage'] = df_cpu_clean[cols_pods_cpu].sum(axis=1)

    # Capacidade CPU
    if 'max capacity' in df_cpu.columns:
        cap_cpu = df_cpu['max capacity'].median()
    else:
        cap_cpu = df_cpu_clean['Total_Usage'].max() * 1.2

    # Estatísticas
    stats = {
        'mem_peak': df_mem_clean['Total_Usage'].max(),
        'mem_cap': cap_mem,
        'mem_sat': (df_mem_clean['Total_Usage'].max() / cap_mem) * 100,
        'cpu_peak': df_cpu_clean['Total_Usage'].max(),
        'cpu_cap': cap_cpu,
        'cpu_sat': (df_cpu_clean['Total_Usage'].max() / cap_cpu) * 100,
        'start': df_cpu_clean['Time'].iloc[0],
        'end': df_cpu_clean['Time'].iloc[-1]
    }

    # Top Consumers
    top_mem = df_mem_clean[cols_pods_mem].agg(['mean', 'max', lambda x: x.quantile(0.95)]).transpose().rename(columns={'<lambda>': 'p95'}).sort_values('mean', ascending=False).head(10)
    top_cpu = df_cpu_clean[cols_pods_cpu].agg(['mean', 'max', lambda x: x.quantile(0.95)]).transpose().rename(columns={'<lambda>': 'p95'}).sort_values('mean', ascending=False).head(10)
    
    top_cpu['burst_ratio'] = top_cpu['max'] / top_cpu['mean'].replace(0, 1)

    return df_mem_clean, df_cpu_clean, stats, top_mem, top_cpu

# --- PLOTAGEM ---

def generate_images(df_mem, df_cpu, stats, top_mem, top_cpu):
    print("Gerando gráficos...")
    plt.style.use('ggplot')
    
    # 1. CPU Saturação
    plt.figure(figsize=(10, 5))
    plt.plot(df_cpu['Time'], df_cpu['Total_Usage'], label='Uso Total', color='#e74c3c')
    plt.axhline(y=stats['cpu_cap'], color='black', linestyle='--', label='Capacidade')
    plt.title('Saturação de CPU vs Capacidade')
    plt.ylabel('Cores')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/cpu_saturacao.png")
    plt.close()

    # 2. Top CPU Bar
    plt.figure(figsize=(10, 6))
    ind = np.arange(len(top_cpu))
    width = 0.35
    plt.barh(ind - width/2, top_cpu['mean'], width, label='Média', color='#3498db')
    plt.barh(ind + width/2, top_cpu['max'], width, label='Pico', color='#e67e22')
    plt.yticks(ind, [n[:40] for n in top_cpu.index], fontsize=8)
    plt.title('Top 10 CPU: Média vs Pico')
    plt.xlabel('Cores')
    plt.legend()
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/cpu_top_services.png")
    plt.close()

    # 3. Top Memória
    plt.figure(figsize=(10, 5))
    top_5_mem = top_mem.index[:5]
    plt.stackplot(df_mem['Time'], [df_mem[c] for c in top_5_mem], labels=[n[:30] for n in top_5_mem], alpha=0.7)
    plt.title('Top 5 Memória ao Longo do Tempo')
    plt.ylabel('MiB')
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/mem_timeline.png")
    plt.close()

# --- MARKDOWN WRITER ---

def write_markdown(stats, top_mem, top_cpu):
    print("Escrevendo relatório Markdown...")
    
    md = f"""# Relatório Técnico de Performance do Prefect

**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Janela de Dados:** {stats['start']} até {stats['end']}

## 1. Resumo Executivo

| Métrica | Valor Atual (Pico) | Capacidade Total | Saturação | Status |
| :--- | :--- | :--- | :--- | :--- |
| **CPU** | {stats['cpu_peak']:.2f} Cores | {stats['cpu_cap']:.1f} Cores | **{stats['cpu_sat']:.1f}%** | {'🔴 CRÍTICO' if stats['cpu_sat'] > 80 else ('🟡 ALERTA' if stats['cpu_sat'] > 70 else '🟢 OK')} |
| **Memória** | {format_bytes(stats['mem_peak'])} | {format_bytes(stats['mem_cap'])} | **{stats['mem_sat']:.1f}%** | {'🔴 CRÍTICO' if stats['mem_sat'] > 90 else ('🟡 ALERTA' if stats['mem_sat'] > 75 else '🟢 OK')} |

### Diagnóstico Automático
"""
    
    if stats['cpu_sat'] > 80:
        md += "- 🚨 **Risco de Throttling:** A CPU atingiu níveis críticos. Serviços podem sofrer lentidão.\n"
    if stats['mem_sat'] > 85:
        md += "- 🚨 **Risco de OOM:** A memória está perigosamente cheia. Pods podem ser reiniciados.\n"
    
    bursty = top_cpu[top_cpu['burst_ratio'] > 4]
    if not bursty.empty:
        md += f"- ⚠️ **Instabilidade:** Foram detectados {len(bursty)} serviços com comportamento 'explosivo' (Pico > 4x Média).\n"

    md += """
---

## 2. Análise de CPU

O gráfico abaixo demonstra o consumo total do cluster em relação à capacidade física do nó.

![Saturação de CPU](cpu_saturacao.png)

### Top 10 Consumidores (Cores)

| Serviço | Média | Pico | Instabilidade (Burst) |
| :--- | :--- | :--- | :--- |
"""
    for name, row in top_cpu.iterrows():
        alert = "🔴" if row['burst_ratio'] > 4 else ""
        md += f"| `{name[:50]}...` | {row['mean']:.3f} | {row['max']:.3f} | {row['burst_ratio']:.1f}x {alert} |\n"

    md += """
> **Nota:** Serviços com alta instabilidade (🔴) são os principais candidatos a causar lentidão repentina no nó.

![Top CPU](cpu_top_services.png)

---

## 3. Análise de Memória

Visualização dos maiores consumidores de memória ao longo do tempo.

![Timeline Memória](mem_timeline.png)

### Top 10 Consumidores

| Serviço | Média | Pico | P95 |
| :--- | :--- | :--- | :--- |
"""
    for name, row in top_mem.iterrows():
        md += f"| `{name[:50]}...` | {format_bytes(row['mean'])} | {format_bytes(row['max'])} | {format_bytes(row['p95'])} |\n"

    md += """
---
*Relatório gerado automaticamente.*
"""

    with open(f"{OUTPUT_DIR}/{OUTPUT_FILE}", "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"\n[SUCESSO] Relatório gerado em: {OUTPUT_DIR}/{OUTPUT_FILE}")

# --- MAIN ---

if __name__ == "__main__":
    res = analyze_data()
    if res:
        df_m, df_c, st, tm, tc = res
        generate_images(df_m, df_c, st, tm, tc)
        write_markdown(st, tm, tc)