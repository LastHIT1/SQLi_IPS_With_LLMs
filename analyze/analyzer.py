import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
import seaborn as sns

INPUT_DIR = '../attack/results/'
RESULTS_PATTERN = 'attack_results_mode_*.csv'
OUTPUT_DIR = 'analyze_results/'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_data():
    search_path = os.path.join(INPUT_DIR, RESULTS_PATTERN)
    files = glob.glob(search_path)

    if not files:
        print(f"No files found matching pattern: {search_path}")
        print(f" Make sure the tester rand and the INPUT_DIR path is correct")
        return None
    
    print(f"\n[+] Found {len(files)} files.")
    dfs = []

    for f  in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    combined_df = pd.concat(dfs, ignore_index=True)
    return combined_df

def calculate_metrics(df):
    results = []
    
    modes = df['Mode'].unique()

    for mode in modes:
        mode_data = df[df['Mode'] == mode]

        tp = len(mode_data[mode_data['Classification'] == 'True Positive'])
        tn = len(mode_data[mode_data['Classification'] == 'True Negative'])
        fp = len(mode_data[mode_data['Classification'] == 'False Positive'])
        fn = len(mode_data[mode_data['Classification'] == 'False Negative'])

        total = tp + tn + fp + fn

        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        average_latency = mode_data['Latency(s)'].mean() * 1000  # Convert to milliseconds

        results.append({
            'Mode': mode,
            'Accuracy': accuracy,
            'Precision': precision,
            'Recall': recall,
            'F1 Score': f1_score,
            'Average Latency (ms)': average_latency,
            'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn
        })

    metrics_df = pd.DataFrame(results).sort_values(by='Mode')
    return metrics_df

def save_metrics_table_image(metrics_df):
    fig, ax = plt.subplots(figsize=(14, len(metrics_df) * 0.8 + 1))
    ax.axis('tight')
    ax.axis('off')

    display_df = metrics_df.copy()
    display_df['Accuracy'] = display_df['Accuracy'].map('{:.3f}'.format)
    display_df['Precision'] = display_df['Precision'].map('{:.3f}'.format)
    display_df['Recall'] = display_df['Recall'].map('{:.3f}'.format)
    display_df['F1 Score'] = display_df['F1 Score'].map('{:.3f}'.format)
    display_df['Average Latency (ms)'] = display_df['Average Latency (ms)'].map('{:.2f} ms'.format)

    table = ax.table(cellText=display_df.values, 
                     colLabels=display_df.columns, 
                     cellLoc='center', 
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#40466e') # Dark blue header
        elif row % 2 == 1:
             cell.set_facecolor('#f2f2f2')

    plt.title('Performance Metrics by Mode', fontsize=16, weight='bold', pad=20)
    plt.tight_layout()

    save_path = f"{OUTPUT_DIR}/performance_metrics_table.png"
    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    print(f"[+] Performance metrics table saved to {save_path}")
    plt.close()

def plot_performance(metrics_df):
    plt.figure(figsize=(12, 8))

    plot_data = metrics_df.melt(id_vars=['Mode'], value_vars=['Accuracy', 'Precision', 'Recall', 'F1 Score'], var_name='Metric', value_name='Score')

    sns.set_style("whitegrid")
    ax = sns.barplot(x='Mode', y='Score', hue='Metric', data=plot_data, palette='viridis')
    ax.set_title('Performance Metrics by Mode')

    plt.ylabel('Score (0.0 - 1.0)')
    plt.xlabel('Mode')
    plt.ylim(0, 1.1)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    for container in ax.containers:
        ax.bar_label(container, fmt='%.2f', padding=3)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/performance_metrics.png")
    print(f"[+] Performance metrics plot saved to {OUTPUT_DIR}/performance_metrics.png")
    plt.close()

def plot_latency(metrics_df):
    plt.figure(figsize=(10, 6))

    sns.set_style("whitegrid")
    ax = sns.barplot(x='Mode', y='Average Latency (ms)', data=metrics_df, palette='magma')
    ax.set_title('Average Latency by Mode')

    plt.ylabel('Time (ms)')
    plt.xlabel('Mode')

    for container in ax.containers:
        ax.bar_label(container, fmt='%.2f ms', padding=3)
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/latency_metrics.png")
    print(f"[+] Latency metrics plot saved to {OUTPUT_DIR}/latency_metrics.png")
    plt.close()

def analyze_bypass(df):
    print("\n" + "-" * 55)
    print("[*] Analyzing bypass attempts...")
    print("[*] THE HALL OF SHAME: Top Bypass Attempts")
    print("-" * 55)

    malicious_df = df[df['Expected'] == 'malicious'].copy()
    malicious_df['Bypassed'] = malicious_df['Classification'].apply(lambda x: 1 if 'False Negative' in x else 0)

    pivot = malicious_df.pivot_table(index='Payload', columns='Mode', values='Bypassed', aggfunc='max', fill_value=0)
    pivot['Total Bypassed'] = pivot.sum(axis=1)

    high_value_targets = pivot.sort_values(by='Total Bypassed', ascending=False)
    top_bypassed = high_value_targets.head(10)

    print(top_bypassed[['Total Bypassed']])

    high_value_targets.to_csv(f"{OUTPUT_DIR}/top_bypass_attempts.csv")
    print(f"\n[+] Top bypass attempts saved to {OUTPUT_DIR}/top_bypass_attempts.csv")

def main():
    print("Web Application Firewall Attack Results Analyzer")
    
    df = load_data()
    if df is None: 
        return
    
    metrics_df = calculate_metrics(df)

    print("\n --- Performance Metrics by Mode ---")
    print(metrics_df[['Mode', 'Accuracy', 'Precision', 'Recall', 'F1 Score', 'Average Latency (ms)']].to_string(index=False))

    metrics_df.to_csv(f"{OUTPUT_DIR}/final_metrics.csv", index=False)
    print(f"\n[+] Final metrics saved to {OUTPUT_DIR}/final_metrics.csv")

    save_metrics_table_image(metrics_df)

    plot_performance(metrics_df)
    plot_latency(metrics_df)

    analyze_bypass(df)

if __name__ == "__main__":
    main()
