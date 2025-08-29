import { useState } from 'react'
import 'antd/dist/reset.css'
import { ConfigProvider, theme, Layout, Typography, Form, Input, InputNumber, Select, Switch, Upload, Button, Space } from 'antd'
import { UploadOutlined } from '@ant-design/icons'

const API_BASE = (import.meta.env.VITE_API_BASE) || (typeof window !== 'undefined' ? (window.location.origin.includes('work-2') ? window.location.origin.replace('work-2', 'work-1') : window.location.origin) : 'http://localhost:12000')

function App() {
  const [songName, setSongName] = useState('')
  const [lyrics, setLyrics] = useState('')
  const [numCovers, setNumCovers] = useState(3)
  const [modelSize, setModelSize] = useState('small')
  const [resolution, setResolution] = useState('1080p')
  const [addSubtitles, setAddSubtitles] = useState(true)
  const [files, setFiles] = useState([])
  const [resultUrl, setResultUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onSubmit = async () => {
    setLoading(true)
    setError('')
    setResultUrl('')
    try {
      const form = new FormData()
      form.append('song_name', songName)
      form.append('lyrics', lyrics)
      form.append('num_covers', String(numCovers))
      form.append('model_size', modelSize)
      form.append('resolution', resolution)
      form.append('add_subtitles', String(addSubtitles))
      for (const f of files) form.append('videos', f)
      const resp = await fetch(`${API_BASE}/api/remix`, { method: 'POST', body: form })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setResultUrl(`${API_BASE}${data.output_url}`)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Layout.Content style={{ maxWidth: 960, margin: '0 auto', padding: 24 }}>
          <Typography.Title level={2}>Auto Remix Covers</Typography.Title>
          <Form layout="vertical" onFinish={onSubmit}>
            <Form.Item label="Song Name" required>
              <Input value={songName} onChange={e=>setSongName(e.target.value)} placeholder="Never Enough" />
            </Form.Item>
            <Space.Compact block>
              <Form.Item label="Num Covers">
                <InputNumber min={1} max={10} value={numCovers} onChange={v=>setNumCovers(v||1)} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Model Size">
                <Select value={modelSize} onChange={setModelSize} options={["tiny","base","small","medium","large-v3"].map(v=>({value:v,label:v}))} />
              </Form.Item>
              <Form.Item label="Resolution">
                <Select value={resolution} onChange={setResolution} options={["720p","1080p","1440p"].map(v=>({value:v,label:v}))} />
              </Form.Item>
              <Form.Item label="Subtitles">
                <Switch checked={addSubtitles} onChange={setAddSubtitles} />
              </Form.Item>
            </Space.Compact>
            <Form.Item label="Lyrics (optional)">
              <Input.TextArea rows={6} value={lyrics} onChange={e=>setLyrics(e.target.value)} placeholder="Paste lyrics here or leave blank to fetch..." />
            </Form.Item>
            <Form.Item label="Upload TikTok/Local MP4s">
              <Upload multiple beforeUpload={() => false} accept="video/mp4" onChange={({ fileList }) => setFiles(fileList.map(f => f.originFileObj).filter(Boolean))}>
                <Button icon={<UploadOutlined />}>Select Files</Button>
              </Upload>
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>Remix</Button>
            </Form.Item>
          </Form>
          {error && <Typography.Text type="danger">{error}</Typography.Text>}
          {resultUrl && (
            <div style={{ marginTop: 16 }}>
              <a href={resultUrl} target="_blank" rel="noreferrer">Download result</a>
              <div style={{ marginTop: 8 }}>
                <video src={resultUrl} controls style={{ width: '100%', maxHeight: 540 }} />
              </div>
            </div>
          )}
        </Layout.Content>
      </Layout>
    </ConfigProvider>
  )
}

export default App
