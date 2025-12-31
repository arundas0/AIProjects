from flask import Flask, render_template_string, request, jsonify
import os
import time

# Import all modules
from config import Config
from parser import HealthDataParser
from analyzer import HealthDataAnalyzer
from ai_service import AIService
from chart_generator import ChartGenerator
from cache import DataCache

# Initialize Flask app
app = Flask(__name__)

# Initialize services
Config.ensure_data_folder()
parser = HealthDataParser(Config.EXPORT_FILE)
cache = DataCache(parser, HealthDataAnalyzer)
ai_service = AIService(Config.OLLAMA_URL, Config.OLLAMA_MODEL, Config.OLLAMA_TIMEOUT)
chart_generator = ChartGenerator()

# Warm up Ollama in the background so app starts immediately
import threading
threading.Thread(target=ai_service.warm_up, daemon=True).start()

# HTML Template (in production, move to templates/index.html)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple Health AI Analyzer</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px;
        }
        .container {
            max-width: 1400px; margin: 0 auto; background: white;
            border-radius: 20px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 30px;
        }
        .header h1 { font-size: 2em; margin-bottom: 5px; }
        .header p { opacity: 0.9; font-size: 0.95em; }
        .main-content { display: grid; grid-template-columns: 350px 1fr; min-height: 600px; }
        .sidebar { background: #f8f9fa; padding: 30px; border-right: 1px solid #e0e0e0; }
        .sidebar h2 { font-size: 1.3em; margin-bottom: 20px; color: #333; }
        .stat-card {
            background: white; padding: 20px; border-radius: 12px;
            margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            font-size: 0.9em; color: #666; margin-bottom: 10px;
            display: flex; align-items: center; gap: 8px;
        }
        .stat-card .value { font-size: 2em; font-weight: bold; color: #333; }
        .stat-card .unit { font-size: 0.8em; color: #999; }
        .stat-card .range { font-size: 0.75em; color: #666; margin-top: 8px; }
        .chat-area { display: flex; flex-direction: column; height: 600px; }
        .messages { flex: 1; overflow-y: auto; padding: 30px; }
        .message { margin-bottom: 20px; display: flex; gap: 10px; }
        .message.user { justify-content: flex-end; }
        .message-content { max-width: 70%; padding: 15px 20px; border-radius: 12px; }
        .message.user .message-content { background: #667eea; color: white; }
        .message.assistant .message-content { background: #f1f3f5; color: #333; }
        .message.system .message-content {
            background: #fff3cd; color: #856404; max-width: 100%; text-align: center;
        }
        .chart-container {
            margin-top: 15px; background: white; padding: 15px;
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .input-area {
            padding: 20px 30px; background: #f8f9fa; border-top: 1px solid #e0e0e0;
            display: flex; gap: 10px;
        }
        .input-area input {
            flex: 1; padding: 15px; border: 2px solid #e0e0e0;
            border-radius: 10px; font-size: 1em; outline: none;
        }
        .input-area input:focus { border-color: #667eea; }
        .input-area button {
            padding: 15px 30px; background: #667eea; color: white;
            border: none; border-radius: 10px; font-size: 1em;
            cursor: pointer; font-weight: 600; transition: background 0.3s;
        }
        .input-area button:hover { background: #5568d3; }
        .input-area button:disabled { background: #ccc; cursor: not-allowed; }
        .loading { display: flex; gap: 5px; padding: 10px; }
        .loading-dot {
            width: 8px; height: 8px; background: #667eea;
            border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both;
        }
        .loading-dot:nth-child(1) { animation-delay: -0.32s; }
        .loading-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        .empty-state { text-align: center; padding: 60px 20px; color: #999; }
        .empty-state h3 { font-size: 1.5em; margin-bottom: 20px; color: #666; }
        .suggestions {
            text-align: left; max-width: 500px; margin: 20px auto;
            background: #f8f9fa; padding: 20px; border-radius: 10px;
        }
        .suggestions ul { list-style: none; }
        .suggestions li {
            padding: 8px 0; color: #666; cursor: pointer; transition: color 0.2s;
        }
        .suggestions li:hover { color: #667eea; }
        .suggestions li:before { content: "💬 "; margin-right: 8px; }
        .error-state { text-align: center; padding: 60px 20px; color: #dc3545; }
        .icon { font-size: 1.2em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Apple Health AI Analyzer</h1>
            <p>AI-powered insights for your health data</p>
        </div>
        <div id="app">
            <div class="main-content">
                <div class="sidebar">
                    <h2>📊 Health Overview</h2>
                    <div id="stats"></div>
                </div>
                <div class="chat-area">
                    <div class="messages" id="messages"></div>
                    <div class="input-area">
                        <input type="text" id="question" placeholder="Ask about your health data..."
                            onkeypress="if(event.key==='Enter') askQuestion()"/>
                        <button onclick="askQuestion()" id="askBtn">Ask AI</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
    <script>
        let healthData = null;
        async function loadHealthData() {
            try {
                const response = await fetch('/api/health-data');
                const data = await response.json();
                if (data.error) { showError(data.error); return; }
                healthData = data;
                renderStats();
                addMessage('system', '✅ Health data loaded successfully! Ask me anything about your health.');
            } catch (error) {
                showError('Failed to load health data: ' + error.message);
            }
        }
        function renderStats() {
            const statsDiv = document.getElementById('stats');
            let html = '';
            if (healthData.steps) {
                html += `<div class="stat-card"><h3><span class="icon">👣</span> Steps</h3>
                    <div class="value">${Math.round(healthData.steps.average).toLocaleString()}</div>
                    <div class="unit">avg/day</div>
                    <div class="range">Range: ${Math.round(healthData.steps.min).toLocaleString()} - ${Math.round(healthData.steps.max).toLocaleString()}</div></div>`;
            }
            if (healthData.heart_rate) {
                html += `<div class="stat-card"><h3><span class="icon">❤️</span> Heart Rate</h3>
                    <div class="value">${Math.round(healthData.heart_rate.average)}</div>
                    <div class="unit">avg bpm</div>
                    <div class="range">Range: ${Math.round(healthData.heart_rate.min)} - ${Math.round(healthData.heart_rate.max)}</div></div>`;
            }
            if (healthData.workouts) {
                html += `<div class="stat-card"><h3><span class="icon">🏃</span> Workouts</h3>
                    <div class="value">${healthData.workouts.total}</div>
                    <div class="unit">sessions</div>
                    <div class="range">${Math.round(healthData.workouts.total_minutes)} minutes total</div></div>`;
            }
            statsDiv.innerHTML = html;
        }
        function showError(message) {
            document.getElementById('messages').innerHTML = `<div class="error-state"><h3>⚠️ Error Loading Data</h3><p>${message}</p></div>`;
        }
        function addMessage(role, content, chartData = null) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            if (chartData) {
                const chartContainer = document.createElement('div');
                chartContainer.className = 'chart-container';
                const canvas = document.createElement('canvas');
                canvas.id = 'chart-' + Date.now();
                chartContainer.appendChild(canvas);
                contentDiv.appendChild(chartContainer);
                messageDiv.appendChild(contentDiv);
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                setTimeout(() => renderChart(canvas.id, chartData), 100);
            } else {
                messageDiv.appendChild(contentDiv);
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        }
        function renderChart(canvasId, chartData) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            if (chartData.type === 'line') {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: chartData.label, data: chartData.data,
                            borderColor: chartData.color, backgroundColor: chartData.color + '20',
                            tension: 0.4
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: true, aspectRatio: 2 }
                });
            } else if (chartData.type === 'bar') {
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: chartData.labels,
                        datasets: [{ label: chartData.label, data: chartData.data, backgroundColor: chartData.colors }]
                    },
                    options: { responsive: true, maintainAspectRatio: true, aspectRatio: 2 }
                });
            }
        }
        async function askQuestion() {
            const input = document.getElementById('question');
            const question = input.value.trim();
            if (!question || !healthData) return;
            input.value = '';
            addMessage('user', question);
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant';
            loadingDiv.innerHTML = `<div class="message-content"><div class="loading">
                <div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div></div>`;
            document.getElementById('messages').appendChild(loadingDiv);
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min timeout
                const response = await fetch('/api/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question }),
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                const data = await response.json();
                loadingDiv.remove();
                addMessage('assistant', data.answer, data.chart);
            } catch (error) {
                loadingDiv.remove();
                addMessage('assistant', 'Error: ' + error.message);
            }
        }
        window.onload = () => {
            loadHealthData();
            if (document.getElementById('messages').children.length === 0) {
                document.getElementById('messages').innerHTML = `<div class="empty-state">
                    <h3>💬 Ask me anything about your health!</h3>
                    <div class="suggestions"><p><strong>Try asking:</strong></p><ul>
                        <li onclick="document.getElementById('question').value = this.textContent.substring(2); askQuestion()">How are my step counts trending?</li>
                        <li onclick="document.getElementById('question').value = this.textContent.substring(2); askQuestion()">What's my average heart rate?</li>
                        <li onclick="document.getElementById('question').value = this.textContent.substring(2); askQuestion()">Analyze my workout patterns</li>
                        <li onclick="document.getElementById('question').value = this.textContent.substring(2); askQuestion()">Am I getting enough exercise?</li>
                        <li onclick="document.getElementById('question').value = this.textContent.substring(2); askQuestion()">What health improvements should I focus on?</li>
                    </ul></div></div>`;
            }
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Render the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/health-data')
def get_health_data():
    """Return parsed health data summary"""
    if not os.path.exists(Config.EXPORT_FILE):
        return jsonify({
            'error': f'Health data file not found at: {Config.EXPORT_FILE}\n\nPlease:\n1. Create folder: {Config.HEALTH_DATA_FOLDER}\n2. Place your export.xml file in it'
        }), 404
    
    try:
        cache.get_data()  # Ensure data is loaded
        analyzer = cache.get_analyzer()
        summary = analyzer.get_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': f'Error parsing health data: {str(e)}'}), 500

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Handle AI questions about health data"""
    question = request.json.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        start = time.perf_counter()
        print(f"[api] /api/ask start question_len={len(question)}")
        analyzer = cache.get_analyzer()
        health_summary = analyzer.get_summary()
        
        # Generate chart if applicable
        chart_data = chart_generator.generate_chart(question, health_summary)
        
        # Get AI response
        ai_response = ai_service.generate_health_insights(health_summary, question)
        elapsed = time.perf_counter() - start
        print(f"[api] /api/ask done duration_s={elapsed:.2f} answer_len={len(ai_response)}")
        
        return jsonify({
            'answer': ai_response,
            'chart': chart_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing question: {str(e)}'}), 500

def main():
    """Main entry point"""
    print("=" * 60)
    print("🏥 Apple Health AI Analyzer")
    print("=" * 60)
    print(f"\n📁 Looking for health data in: {os.path.abspath(Config.HEALTH_DATA_FOLDER)}")
    print(f"📄 Export file: {os.path.abspath(Config.EXPORT_FILE)}")
    print("\n⚙️  Requirements:")
    print("  1. Place your export.xml in the health_data folder")
    print("  2. Make sure Ollama is running: ollama serve")
    print("  3. Pull model: ollama pull llama3.2")
    print(f"\n🚀 Starting server at http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print("=" * 60 + "\n")
    
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.DEBUG)

if __name__ == '__main__':
    main()
