def generate_report(dataset_name: str, stats: dict, applied_actions: list) -> str:
    """
    Generates a professional HTML report summarizing the "Before vs. After" statistics
    and listing the cleaning actions applied. Saves to a file and returns the path.
    """
    actions_html = "".join([f"<li>{item['action']} on <b>{item.get('column', 'Dataset')}</b></li>" for item in applied_actions])
    
    pre_score = stats.get('pre_cleaning_score', 0)
    post_score = stats.get('post_cleaning_score', 0)
    
    score_color = "#28a745" if post_score >= pre_score else "#dc3545"

    html_content = f"""
    <html>
        <head>
            <title>Data Cleaning Report: {dataset_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f7f6; color: #333; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .container {{ background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
                .stat-box {{ background-color: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; border-left: 5px solid #3498db; }}
                .score-box {{ background-color: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; border-left: 5px solid {score_color}; }}
                .score {{ font-size: 1.5em; font-weight: bold; color: #2c3e50; }}
                .actions {{ margin-top: 30px; background-color: #eaf2f8; padding: 15px; border-radius: 8px; }}
                ul {{ line-height: 1.6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Data Cleaning Report for {dataset_name}</h1>
                
                <div class="stats-grid">
                    <div class="score-box">
                        <p>Pre-Cleaning Score</p>
                        <p class="score">{pre_score}/100</p>
                    </div>
                    <div class="score-box">
                        <p>Post-Cleaning Score</p>
                        <p class="score">{post_score}/100</p>
                    </div>
                    <div class="stat-box">
                        <p><strong>Rows:</strong> {stats.get('initial_rows')} &rarr; {stats.get('final_rows')}</p>
                        <p><strong>Columns:</strong> {stats.get('initial_cols')} &rarr; {stats.get('final_cols')}</p>
                    </div>
                    <div class="stat-box">
                        <p><strong>Missing Values Fixed:</strong> {stats.get('missing_removed')}</p>
                        <p>Total Remaining: {stats.get('final_missing')}</p>
                    </div>
                </div>
                
                <div class="actions">
                    <h3>Applied Actions:</h3>
                    <ul>
                        {actions_html}
                    </ul>
                </div>
            </div>
        </body>
    </html>
    """
    
    report_path = f"{dataset_name}_report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return report_path
