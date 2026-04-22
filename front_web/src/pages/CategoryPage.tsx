import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, X } from 'lucide-react'
import { fetchCategories } from '../lib/supabase'
import { categoryApi } from '../lib/api'
import { Modal, ConfirmDialog } from '../components/ui/Modal'

type Category = Record<string, unknown>

interface FormData {
  code: string
  name_ko: string
  name_en: string
  sort_order: number
  keywords: string[]
}

const EMPTY_FORM: FormData = { code: '', name_ko: '', name_en: '', sort_order: 0, keywords: [] }

function KeywordInput({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('')

  const add = () => {
    const t = input.trim()
    if (t && !value.includes(t)) onChange([...value, t])
    setInput('')
  }

  return (
    <div>
      <div className="flex gap-2 mb-2">
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          placeholder="키워드 입력 후 Enter"
          className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm outline-none focus:border-primary" />
        <button type="button" onClick={add}
          className="px-3 py-1.5 text-xs rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 font-medium">추가</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {value.map(k => (
          <span key={k} className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary font-medium">
            {k}
            <button type="button" onClick={() => onChange(value.filter(x => x !== k))} className="hover:text-primary/60">
              <X size={10} />
            </button>
          </span>
        ))}
      </div>
    </div>
  )
}

function CategoryForm({ initial, isEdit, onSave, onCancel }: {
  initial: FormData
  isEdit: boolean
  onSave: (data: FormData) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState<FormData>(initial)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k: keyof FormData, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await onSave(form)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '저장 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">코드</label>
          <input required disabled={isEdit} value={form.code} onChange={e => set('code', e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary disabled:bg-gray-50 disabled:text-gray-400 font-mono" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">정렬 순서</label>
          <input type="number" required value={form.sort_order} onChange={e => set('sort_order', Number(e.target.value))}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary font-mono" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">이름 (한국어)</label>
          <input required value={form.name_ko} onChange={e => set('name_ko', e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">이름 (영어)</label>
          <input required value={form.name_en} onChange={e => set('name_en', e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary" />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">키워드</label>
        <KeywordInput value={form.keywords} onChange={v => set('keywords', v)} />
      </div>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{error}</p>}
      <div className="flex gap-2 justify-end pt-2">
        <button type="button" onClick={onCancel} className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">취소</button>
        <button type="submit" disabled={loading} className="px-4 py-2 text-sm rounded-lg bg-primary text-white font-medium hover:bg-primary/90 disabled:opacity-60">
          {loading ? '저장 중...' : '저장'}
        </button>
      </div>
    </form>
  )
}

export function CategoryPage() {
  const qc = useQueryClient()
  const { data: categories = [], isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  })

  const [creating, setCreating] = useState(false)
  const [editing, setEditing]   = useState<Category | null>(null)
  const [deleting, setDeleting] = useState<Category | null>(null)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['categories'] })

  const handleCreate = async (form: FormData) => {
    await categoryApi.create(form)
    await invalidate()
    setCreating(false)
  }

  const handleUpdate = async (form: FormData) => {
    await categoryApi.update(form.code, form)
    await invalidate()
    setEditing(null)
  }

  const handleDelete = async () => {
    if (!deleting) return
    await categoryApi.remove(deleting.code as string)
    await invalidate()
    setDeleting(null)
  }

  const toForm = (row: Category): FormData => ({
    code:       row.code as string,
    name_ko:    row.name_ko as string,
    name_en:    row.name_en as string,
    sort_order: row.sort_order as number,
    keywords:   (row.keywords as string[]) ?? [],
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">카테고리 관리</h1>
        <button onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-primary text-white font-medium hover:bg-primary/90">
          <Plus size={14} />신규 카테고리
        </button>
      </div>

      <div className="rounded-xl bg-white border border-gray-100 overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-sm text-gray-400">로딩 중...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium w-24">코드</th>
                <th className="px-4 py-2.5 text-left font-medium">이름</th>
                <th className="px-4 py-2.5 text-left font-medium">키워드</th>
                <th className="px-4 py-2.5 text-center font-medium w-20">정렬</th>
                <th className="px-4 py-2.5 text-center font-medium w-24">관리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {categories.map((row: Category) => (
                <tr key={row.code as string} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-primary">{row.code as string}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{row.name_ko as string}</p>
                    <p className="text-xs text-gray-400">{row.name_en as string}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {((row.keywords as string[]) ?? []).slice(0, 5).map(k => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{k}</span>
                      ))}
                      {((row.keywords as string[]) ?? []).length > 5 && (
                        <span className="text-[10px] text-gray-400">+{((row.keywords as string[]).length - 5)}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center font-mono text-xs text-gray-500">{row.sort_order as number}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1.5">
                      <button onClick={() => setEditing(row)}
                        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-primary transition-colors">
                        <Pencil size={13} />
                      </button>
                      <button onClick={() => setDeleting(row)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors">
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal open={creating} onClose={() => setCreating(false)} title="신규 카테고리">
        <CategoryForm initial={EMPTY_FORM} isEdit={false} onSave={handleCreate} onCancel={() => setCreating(false)} />
      </Modal>

      <Modal open={!!editing} onClose={() => setEditing(null)} title="카테고리 수정">
        {editing && (
          <CategoryForm initial={toForm(editing)} isEdit onSave={handleUpdate} onCancel={() => setEditing(null)} />
        )}
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="카테고리 삭제"
        message={`"${deleting?.name_ko as string}" 카테고리를 삭제하시겠습니까? 연결된 인과관계 데이터에 영향을 줄 수 있습니다.`}
        confirmLabel="삭제"
        danger
      />
    </div>
  )
}
