import { useEffect, useRef, useState } from 'react'
import { Dialog, DialogContent, DialogTitle, Alert, CircularProgress } from '@mui/material'
import { ExternalLink } from 'lucide-react'
import { api, errorText, previewFile } from '../lib/api'
import type { Citation, EvidenceDetail } from '../lib/types'

export default function EvidencePreview({ citation, onClose }: { citation: Citation | null; onClose: () => void }) {
  const [detail, setDetail] = useState<EvidenceDetail | null>(null)
  const [image, setImage] = useState('')
  const [media, setMedia] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const audioPlayer = useRef<HTMLAudioElement>(null)
  const videoPlayer = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (!citation) return
    let live = true
    const urls: string[] = []
    setDetail(null); setImage(''); setMedia(''); setError(''); setLoading(true)
    const load = async () => {
      try {
        const { data } = await api.get<EvidenceDetail>(`/files/${citation.file_id}/evidence/${citation.chunk_id}`)
        if (!live) return
        setDetail(data)
        if (data.can_render) {
          const response = await api.get(`/files/${citation.file_id}/evidence/${citation.chunk_id}/image`, { responseType: 'blob' })
          if (live) { const url = URL.createObjectURL(response.data); urls.push(url); setImage(url) }
        }
        if (data.locator.kind === 'audio' || data.locator.kind === 'video') {
          const response = await api.get(`/files/${citation.file_id}/preview`, { responseType: 'blob' })
          if (live) { const url = URL.createObjectURL(response.data); urls.push(url); setMedia(url) }
        }
      } catch (exception) { if (live) setError(errorText(exception)) }
      finally { if (live) setLoading(false) }
    }
    load()
    return () => { live = false; urls.forEach(URL.revokeObjectURL) }
  }, [citation?.file_id, citation?.chunk_id])

  useEffect(() => {
    const player = audioPlayer.current || videoPlayer.current
    if (media && player && detail) player.currentTime = detail.locator.start_seconds ?? detail.locator.second ?? 0
  }, [media, detail])

  return <Dialog open={Boolean(citation)} onClose={onClose} fullWidth maxWidth="md" aria-labelledby="evidence-title">
    <DialogTitle id="evidence-title">Source evidence · {citation?.file_name}</DialogTitle>
    <DialogContent>
      {loading && <CircularProgress size={20}/>}
      {error && <Alert severity="error">{error}</Alert>}
      {detail && <div className="space-y-4 text-sm">
        <p className="muted">Version {detail.version} · {detail.location} · locator precision: {detail.precision.replaceAll('_', ' ')}. Highlighting may cover a page or OCR region rather than the exact sentence.</p>
        {image && <img src={image} alt={`Located source at ${detail.location}`} className="max-h-110 mx-auto object-contain rounded-lg"/>}
        {media && detail.locator.kind === 'audio' && <audio ref={audioPlayer} src={media} controls className="w-full"/>}
        {media && detail.locator.kind === 'video' && <video ref={videoPlayer} src={media} controls className="max-h-100 w-full"/>}
        {(detail.locator.start_seconds !== undefined || detail.locator.second !== undefined) && <p>Starts at {detail.locator.start_seconds ?? detail.locator.second}s{detail.locator.end_seconds !== undefined ? `; ends near ${detail.locator.end_seconds}s` : ''}.</p>}
        <div className="raised p-4"><p className="font-semibold mb-2">Indexed passage</p><p className="whitespace-pre-wrap leading-6">{detail.text}</p></div>
        <p className="muted">Extraction: {detail.quality.method || 'unknown'}{detail.quality.flags?.length ? ` · review ${detail.quality.flags.join(', ')}` : ''}{detail.quality.ocr_signal !== undefined && detail.quality.ocr_signal !== null ? ` · OCR engine signal ${detail.quality.ocr_signal}` : ''}</p>
        {detail.quality.note && <p className="muted">{detail.quality.note}</p>}
        <button className="outline flex gap-2 items-center" onClick={() => previewFile(detail.file_id).catch(exception => setError(errorText(exception)))}>Open original <ExternalLink size={16}/></button>
      </div>}
    </DialogContent>
  </Dialog>
}
