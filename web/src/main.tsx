import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

function App() {
  const [status, setStatus] = useState('检查中')
  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/ready', { signal: controller.signal })
      .then(response => setStatus(response.ok ? '已就绪' : '未就绪'))
      .catch(() => { if (!controller.signal.aborted) setStatus('无法连接') })
    return () => controller.abort()
  }, [])
  return <main><h1>LYT 公司系统</h1><p role="status">后端状态：{status}</p></main>
}
createRoot(document.getElementById('root')!).render(<App />)
