import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-crash">
          <img src="/riceai-logo.png" alt="" />
          <h1>RiceAI chưa tải được</h1>
          <p>Trang gặp lỗi khi hiển thị. Hãy tải lại; nếu vẫn còn, gửi dòng lỗi bên dưới để mình sửa ngay.</p>
          <code>{this.state.error.message}</code>
          <button type="button" onClick={() => window.location.reload()}>Tải lại trang</button>
        </main>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AppErrorBoundary>
  </React.StrictMode>,
)
