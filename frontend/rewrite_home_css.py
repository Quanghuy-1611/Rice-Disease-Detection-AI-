import os

css_content = """
/* Enhanced Home CSS */
.home-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-section {
  text-align: center;
  padding: 3rem 1rem;
  background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0));
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
}

.hero-content h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.hero-content .highlight {
  color: #10b981;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}

.hero-content p {
  font-size: 1.1rem;
  color: #a7f3d0;
  max-width: 600px;
  margin: 0 auto 2rem;
}

.hero-features {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.hero-features span {
  background: rgba(16, 185, 129, 0.2);
  padding: 0.5rem 1rem;
  border-radius: 50px;
  font-size: 0.9rem;
  font-weight: 500;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.main-panel {
  padding: 2rem;
}

.how-it-works {
  margin-top: 3rem;
  text-align: center;
}

.how-it-works h3 {
  font-size: 1.5rem;
  margin-bottom: 2rem;
  color: #fff;
}

.steps-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
}

.step {
  background: rgba(0, 0, 0, 0.2);
  padding: 1.5rem;
  border-radius: 15px;
  position: relative;
  transition: transform 0.3s ease;
}

.step:hover {
  transform: translateY(-5px);
}

.step-number {
  position: absolute;
  top: -15px;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 30px;
  background: #10b981;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4);
}

.step h4 {
  margin-top: 1rem;
  color: #6ee7b7;
}

.step p {
  font-size: 0.9rem;
  color: #cbd5e1;
}

/* Detailed Result Card */
.detailed-result-card {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  padding: 2rem;
  margin-top: 2rem;
  animation: fadeIn 0.5s ease-out;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.result-header h3 {
  margin: 0;
  color: #fff;
}

.disease-widgets {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin: 1.5rem 0;
}

.widget {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.widget-icon {
  font-size: 1.5rem;
}

.widget-content strong {
  display: block;
  margin-bottom: 0.5rem;
  color: #94a3b8;
  font-size: 0.9rem;
}

.widget-content p {
  margin: 0;
  font-size: 0.9rem;
  color: #fff;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 50px;
  font-size: 0.8rem;
  font-weight: bold;
}

.badge.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
.badge.medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }
.badge.low { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }

.result-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-chat-ai {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
}

.btn-chat-ai:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

@media (max-width: 768px) {
  .disease-widgets {
    grid-template-columns: 1fr;
  }
  .result-actions {
    flex-direction: column;
  }
}
"""

with open(r"D:\Phát hiện bệnh cây lúa\frontend\src\pages\Home.css", "a", encoding="utf-8") as f:
    f.write(css_content)
