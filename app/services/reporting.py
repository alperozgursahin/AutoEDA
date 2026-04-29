def generate_report(dataset_name: str, pre_score: float, post_score: float, applied_actions: list) -> str:
    """
    Generates a simple HTML report summarizing the "Before vs. After" statistics
    and listing the cleaning actions applied.
    """
    actions_html = "".join([f"<li>{item['action']} on <b>{item['column']}</b></li>" for item in applied_actions])
    
    html_content = f"""
    <html>
        <head>
            <title>Data Cleaning Report: {dataset_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                .score-card {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .score {{ font-size: 1.2em; }}
                .actions {{ margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>Data Cleaning Report for {dataset_name}</h1>
            
            <div class="score-card">
                <p class="score"><strong>Pre-Cleaning Score:</strong> {pre_score}</p>
                <p class="score"><strong>Post-Cleaning Score:</strong> {post_score}</p>
            </div>
            
            <div class="actions">
                <h3>Applied Actions:</h3>
                <ul>
                    {actions_html}
                </ul>
            </div>
        </body>
    </html>
    """
    return html_content
