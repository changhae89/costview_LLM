import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, RotateCcw } from 'lucide-react'
import { categoryApi, consumerItemApi } from '../lib/api'
import { Modal, ConfirmDialog } from '../components/ui/Modal'
import { formatDate } from '../lib/helpers'

type Item = Record<string, unknown>
type Category = Record<string, unknown>

interface FormData {
  category_code: string
  name_ko: string
  name_en: string
  unit: string
  typical_monthly_spend: number | ''
  weight: number | ''
  description: string
}

const EMPTY_FORM: FormData = {
  category_code: '',
  name_ko: '',
  name_en: '',
  unit: '',
  typical_monthly_spend: '',
  weight: '',
  description: '',
}

function ItemForm({ initial, categories, onSave, onCancel }: {
  initial: FormData
  categories: Category[]
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
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">카테고리</label>
        <select required value={form.category_code} onChange={e => set('category_code', e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary bg-white">
          <option value="">선택...</option>
          {categories.map((c: Category) => (
            <option key={c.code as string} value={c.code as string}>{c.name_ko as string}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">이름 (한국어)</label>
          <input required value={form.name_ko} onChange={e => set('name_ko', e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">이름 (영어)</label>
          <input value={form.name_en} onChange={e => set('name_en', e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">단위</label>
          <input required value={form.unit} onChange={e => set('unit', e.target.value)}
            placeholder="예: 개, kg, L, 회"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">월 지출액 (원)</label>
          <input type="number" value={form.typical_monthly_spend} onChange={e => set('typical_monthly_spend', e.target.value ? Number(e.target.value) : '')}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary font-mono" />
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-600 mb-1">가중치</label>
          <input type="number" step="0.01" value={form.weight} onChange={e => set('weight', e.target.value ? Number(e.target.value) : '')}
            placeholder="0.00 ~ 1.00"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary font-mono" />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">설명</label>
        <textarea value={form.description} onChange={e => set('description', e.target.value)} rows={2}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary resize-none" />
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

export function ConsumerItemPage() {
  const qc = useQueryClient()
  const [showDeleted, setShowDeleted] = useState(false)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing]   = useState<Item | null>(null)
  const [deleting, setDeleting] = useState<Item | null>(null)
  const [restoring, setRestoring] = useState<Item | null>(null)
  const [search, setSearch]     = useState('')

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['consumerItems', showDeleted],
    queryFn: () => consumerItemApi.list(showDeleted),
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: categoryApi.list,
  })

  const catMap = Object.fromEntries((categories as Category[]).map((c: Category) => [c.code, c.name_ko]))

  const filtered = (items as Item[]).filter((row: Item) =>
    !search || (row.name_ko as string)?.toLowerCase().includes(search.toLowerCase())
  )

  const invalidate = () => qc.invalidateQueries({ queryKey: ['consumerItems'] })

  const handleCreate = async (form: FormData) => {
    await consumerItemApi.create(form)
    await invalidate()
    setCreating(false)
  }

  const handleUpdate = async (form: FormData) => {
    await consumerItemApi.update(editing!.id as string, form)
    await invalidate()
    setEditing(null)
  }

  const handleDelete = async () => {
    if (!deleting) return
    await consumerItemApi.remove(deleting.id as string)
    await invalidate()
    setDeleting(null)
  }

  const handleRestore = async () => {
    if (!restoring) return
    await consumerItemApi.restore(restoring.id as string)
    await invalidate()
    setRestoring(null)
  }

  const toForm = (row: Item): FormData => ({
    category_code:          row.category_code as string ?? '',
    name_ko:                row.name_ko as string ?? '',
    name_en:                row.name_en as string ?? '',
    unit:                   row.unit as string ?? '',
    typical_monthly_spend:  row.typical_monthly_spend as number ?? '',
    weight:                 row.weight as number ?? '',
    description:            row.description as string ?? '',
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">소비 항목 관리</h1>
        <button onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-primary text-white font-medium hover:bg-primary/90">
          <Plus size={14} />신규 항목
        </button>
      </div>

      {/* 필터 바 */}
      <div className="flex flex-wrap gap-3 items-center rounded-xl bg-white p-3 border border-gray-100">
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="항목명 검색..."
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm w-48 outline-none focus:border-primary" />
        <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer ml-auto">
          <input type="checkbox" checked={showDeleted} onChange={e => setShowDeleted(e.target.checked)} className="rounded" />
          삭제 항목 포함
        </label>
        <span className="font-mono text-xs text-gray-400">총 {filtered.length.toLocaleString()}건</span>
      </div>

      <div className="rounded-xl bg-white border border-gray-100 overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-sm text-gray-400">로딩 중...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">항목명</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">카테고리</th>
                <th className="px-4 py-2.5 text-left font-medium w-16">단위</th>
                <th className="px-4 py-2.5 text-right font-medium w-28">월 지출액</th>
                <th className="px-4 py-2.5 text-right font-medium w-20">가중치</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">등록일</th>
                <th className="px-4 py-2.5 text-center font-medium w-24">관리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((row: Item) => {
                const deleted = !!row.is_deleted
                return (
                  <tr key={row.id as string} className={`hover:bg-gray-50 transition-colors ${deleted ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{row.name_ko as string}</p>
                      {!!row.name_en && <p className="text-xs text-gray-400">{row.name_en as string}</p>}
                      {!!row.description && <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{row.description as string}</p>}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {catMap[row.category_code as string] ?? row.category_code as string}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.unit as string}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-700 text-right">
                      {row.typical_monthly_spend != null ? `₩${(row.typical_monthly_spend as number).toLocaleString()}` : '-'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500 text-right">
                      {row.weight != null ? (row.weight as number).toFixed(2) : '-'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{formatDate(row.created_at as string)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-1.5">
                        {deleted ? (
                          <button onClick={() => setRestoring(row)}
                            className="p-1.5 rounded-lg hover:bg-green-50 text-gray-400 hover:text-green-600 transition-colors" title="복원">
                            <RotateCcw size={13} />
                          </button>
                        ) : (
                          <>
                            <button onClick={() => setEditing(row)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-primary transition-colors" title="수정">
                              <Pencil size={13} />
                            </button>
                            <button onClick={() => setDeleting(row)}
                              className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors" title="삭제">
                              <Trash2 size={13} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="py-12 text-center text-sm text-gray-400">항목이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <Modal open={creating} onClose={() => setCreating(false)} title="신규 소비 항목">
        <ItemForm initial={EMPTY_FORM} categories={categories as Category[]} onSave={handleCreate} onCancel={() => setCreating(false)} />
      </Modal>

      <Modal open={!!editing} onClose={() => setEditing(null)} title="소비 항목 수정">
        {editing && (
          <ItemForm initial={toForm(editing)} categories={categories as Category[]} onSave={handleUpdate} onCancel={() => setEditing(null)} />
        )}
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="항목 삭제"
        message={`"${deleting?.name_ko as string}" 항목을 삭제하시겠습니까? (소프트 삭제)`}
        confirmLabel="삭제"
        danger
      />

      <ConfirmDialog
        open={!!restoring}
        onClose={() => setRestoring(null)}
        onConfirm={handleRestore}
        title="항목 복원"
        message={`"${restoring?.name_ko as string}" 항목을 복원하시겠습니까?`}
        confirmLabel="복원"
      />
    </div>
  )
}
