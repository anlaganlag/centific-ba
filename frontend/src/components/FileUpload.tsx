import { useState, useRef } from 'react'
import api from '../lib/api'

interface Props {
  projectId: string
  onUploaded: () => void
}

export default function FileUpload({ projectId, onUploaded }: Props) {
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const upload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    setProgress(0)
    setStatusText(`Uploading ${files.length} file${files.length > 1 ? 's' : ''}...`)
    try {
      const formData = new FormData()
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i])
      }
      await api.post(`/documents/upload/${projectId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) {
            const pct = Math.round((e.loaded / e.total) * 100)
            setProgress(pct)
            if (pct >= 100) {
              setStatusText('Processing documents (parsing, chunking, embedding)...')
            } else {
              setStatusText(`Uploading... ${pct}%`)
            }
          }
        },
      })
      setStatusText('Done!')
      onUploaded()
    } catch (err) {
      console.error('Upload failed', err)
      setStatusText('Upload failed')
    } finally {
      setTimeout(() => {
        setUploading(false)
        setProgress(0)
        setStatusText('')
      }, 1500)
    }
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); upload(e.dataTransfer.files) }}
      onClick={() => !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => upload(e.target.files)}
      />
      {uploading ? (
        <div className="space-y-3">
          <div className="flex items-center justify-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full" />
            <p className="text-gray-600 text-sm font-medium">{statusText}</p>
          </div>
          {progress > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-2 max-w-xs mx-auto">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      ) : (
        <div>
          <p className="text-gray-600 font-medium">Drop files here or click to upload</p>
          <p className="text-gray-400 text-sm mt-1">PDF, DOCX, PPTX, TXT, CSV, images</p>
        </div>
      )}
    </div>
  )
}
