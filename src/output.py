"""Output generation: CSV, Excel, HTML reports."""

from datetime import datetime
from pathlib import Path
from typing import List
import pandas as pd

from src.models import ScreeningResult, BullPutSpread
from src.config import CONFIG


def save_csv(result: ScreeningResult, filepath: str = None) -> str:
    """Save results to CSV."""
    if filepath is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = Path(CONFIG.output_dir) / f"bull_put_spreads_{timestamp}.csv"

    df = result.to_dataframe()
    if not df.empty:
        df.to_csv(filepath, index=False)
    else:
        # Create empty file with headers
        pd.DataFrame(columns=df.columns).to_csv(filepath, index=False)
    return str(filepath)


def save_excel(result: ScreeningResult, filepath: str = None) -> str:
    """Save results to Excel with formatting."""
    if filepath is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = Path(CONFIG.output_dir) / f"bull_put_spreads_{timestamp}.xlsx"

    df = result.to_dataframe()

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        if not df.empty:
            df.to_excel(writer, sheet_name='Spreads', index=False)
            ws = writer.sheets['Spreads']
            # Auto-fit columns
            for col in ws.columns:
                max_len = max(len(str(cell.value)) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = max_len + 2
        else:
            pd.DataFrame().to_excel(writer, sheet_name='Spreads', index=False)

        # Summary sheet
        summary = pd.DataFrame({
            'Metric': ['Timestamp', 'Symbols Scanned', 'Spreads Found', 'Top N Selected',
                       'Max Positions', 'Stop Multiplier', 'Profit Target'],
            'Value': [result.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                      result.scanned_symbols, len(result.spreads), CONFIG.top_n,
                      CONFIG.max_positions, CONFIG.stop_multiplier, CONFIG.profit_target]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

    return str(filepath)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bull Put Spread Screener - {{ timestamp }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 6px; }
        .meta-item { }
        .meta-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .meta-value { font-size: 18px; font-weight: bold; color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #4CAF50; color: white; font-weight: 600; position: sticky; top: 0; }
        tr:hover { background: #f5f5f5; }
        .positive { color: #4CAF50; font-weight: bold; }
        .negative { color: #f44336; }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin: 30px 0; }
        .chart-container { background: #fafafa; padding: 15px; border-radius: 6px; }
        .error { color: #f44336; background: #fff3f3; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Bull Put Spread Screener</h1>

        <div class="meta">
            <div class="meta-item">
                <div class="meta-label">Run Time</div>
                <div class="meta-value">{{ timestamp }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Symbols Scanned</div>
                <div class="meta-value">{{ scanned_symbols }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Spreads Found</div>
                <div class="meta-value">{{ spreads_found }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Top N Selected</div>
                <div class="meta-value">{{ top_n }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Max Positions</div>
                <div class="meta-value">{{ max_positions }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Stop / Target</div>
                <div class="meta-value">{{ stop_mult }}x / {{ profit_target }}%</div>
            </div>
        </div>

        {% if errors %}
        <div class="error">
            <strong>⚠️ Errors:</strong>
            <ul>{% for e in errors %}<li>{{ e }}</li>{% endfor %}</ul>
        </div>
        {% endif %}

        <div class="charts">
            <div class="chart-container">
                <canvas id="creditPopChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="dteChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="rrChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="sectorChart"></canvas>
            </div>
        </div>

        <h2>Top {{ top_n }} Bull Put Spreads</h2>
        <table id="spreadsTable">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Expiry</th>
                    <th>DTE</th>
                    <th>Short Strike</th>
                    <th>Long Strike</th>
                    <th>Width</th>
                    <th>Credit</th>
                    <th>Max Profit</th>
                    <th>Max Loss</th>
                    <th>PoP %</th>
                    <th>Short Δ</th>
                    <th>Long Δ</th>
                    <th>Short Vol</th>
                    <th>Long Vol</th>
                    <th>Underlying</th>
                    <th>R/R</th>
                    <th>Cr%Width</th>
                    <th>Break Even</th>
                </tr>
            </thead>
            <tbody>
                {% for s in spreads %}
                <tr>
                    <td><strong>{{ s.Symbol }}</strong></td>
                    <td>{{ s.Expiry }}</td>
                    <td>{{ s.DTE }}</td>
                    <td>{{ s['Short Strike'] }}</td>
                    <td>{{ s['Long Strike'] }}</td>
                    <td>{{ s.Width }}</td>
                    <td class="positive">${{ s.Credit }}</td>
                    <td class="positive">${{ s['Max Profit'] }}</td>
                    <td class="negative">${{ s['Max Loss'] }}</td>
                    <td><strong>{{ s.PoP }}%</strong></td>
                    <td>{{ s['Short Delta'] }}</td>
                    <td>{{ s['Long Delta'] }}</td>
                    <td>{{ s['Short Vol'] }}</td>
                    <td>{{ s['Long Vol'] }}</td>
                    <td>${{ s.Underlying }}</td>
                    <td>{{ s['R/R'] }}</td>
                    <td>{{ s['Credit%Width'] }}%</td>
                    <td>${{ s['Break Even'] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        {% if spreads|length == 0 %}
        <p style="text-align: center; color: #666; margin-top: 40px;">No spreads found matching criteria.</p>
        {% endif %}
    </div>

    <script>
        // Chart data
        const spreads = {{ spreads_json | safe }};

        // Credit vs PoP scatter
        new Chart(document.getElementById('creditPopChart'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Spreads',
                    data: spreads.map(s => ({ x: s.PoP, y: s.Credit, symbol: s.Symbol })),
                    backgroundColor: 'rgba(76, 175, 80, 0.6)',
                    borderColor: '#4CAF50'
                }]
            },
            options: {
                responsive: true,
                plugins: { title: { display: true, text: 'Credit vs Probability of Profit' } },
                scales: {
                    x: { title: { display: true, text: 'PoP (%)' }, min: 0, max: 100 },
                    y: { title: { display: true, text: 'Credit ($)' } }
                }
            }
        });

        // DTE distribution
        const dteCounts = {};
        spreads.forEach(s => { dteCounts[s.DTE] = (dteCounts[s.DTE] || 0) + 1; });
        new Chart(document.getElementById('dteChart'), {
            type: 'bar',
            data: {
                labels: Object.keys(dteCounts).sort((a,b)=>a-b),
                datasets: [{
                    label: 'Count',
                    data: Object.keys(dteCounts).sort((a,b)=>a-b).map(k => dteCounts[k]),
                    backgroundColor: 'rgba(33, 150, 243, 0.6)',
                    borderColor: '#2196F3'
                }]
            },
            options: { responsive: true, plugins: { title: { display: true, text: 'DTE Distribution' } } }
        });

        // Risk/Reward
        new Chart(document.getElementById('rrChart'), {
            type: 'bar',
            data: {
                labels: spreads.slice(0, 10).map(s => s.Symbol),
                datasets: [{
                    label: 'Risk/Reward',
                    data: spreads.slice(0, 10).map(s => s['R/R']),
                    backgroundColor: 'rgba(255, 152, 0, 0.6)',
                    borderColor: '#FF9800'
                }]
            },
            options: { responsive: true, plugins: { title: { display: true, text: 'Top 10 Risk/Reward' } }, indexAxis: 'y' }
        });

        // Sector would need sector data - placeholder
        new Chart(document.getElementById('sectorChart'), {
            type: 'doughnut',
            data: {
                labels: ['Tech', 'Finance', 'Healthcare', 'Consumer', 'Other'],
                datasets: [{
                    data: [30, 25, 15, 20, 10],
                    backgroundColor: ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#607D8B']
                }]
            },
            options: { responsive: true, plugins: { title: { display: true, text: 'Sector Distribution (Placeholder)' } } }
        });
    </script>
</body>
</html>
"""


def save_html(result: ScreeningResult, filepath: str = None) -> str:
    """Save results to interactive HTML report."""
    from jinja2 import Template

    if filepath is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = Path(CONFIG.output_dir) / f"bull_put_spreads_{timestamp}.html"

    df = result.to_dataframe()
    spreads_data = df.to_dict('records') if not df.empty else []

    template = Template(HTML_TEMPLATE)
    html = template.render(
        timestamp=result.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        scanned_symbols=result.scanned_symbols,
        spreads_found=len(result.spreads),
        top_n=CONFIG.top_n,
        max_positions=CONFIG.max_positions,
        stop_mult=CONFIG.stop_multiplier,
        profit_target=int(CONFIG.profit_target * 100),
        errors=result.errors,
        spreads=spreads_data,
        spreads_json=spreads_data
    )

    Path(filepath).write_text(html, encoding='utf-8')
    return str(filepath)


def generate_all_reports(result: ScreeningResult) -> dict:
    """Generate all report formats."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = Path(CONFIG.output_dir) / f"bull_put_spreads_{timestamp}"

    return {
        'csv': save_csv(result, str(base) + '.csv'),
        'excel': save_excel(result, str(base) + '.xlsx'),
        'html': save_html(result, str(base) + '.html')
    }