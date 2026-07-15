import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getConsultation, transitionConsultation } from '../api/client'
import { ALLOWED_TRANSITIONS, type ConsultationStatus } from '../api/types'
import { PriorityBadge, StatusBadge } from '../components/StatusBadge'

export default function ConsultationDetailPage() {
  const { id } = useParams()
  const consultId = Number(id)
  const queryClient = useQueryClient()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['consultation', consultId],
    queryFn: () => getConsultation(consultId),
    enabled: Number.isFinite(consultId),
  })

  const mutation = useMutation({
    mutationFn: (toStatus: ConsultationStatus) =>
      transitionConsultation(consultId, toStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consultation', consultId] })
      queryClient.invalidateQueries({ queryKey: ['consultations'] })
    },
  })

  if (isLoading) return <p className="muted">Loading…</p>
  if (isError) return <p className="error">{(error as Error).message}</p>
  if (!data) return null

  const nextStates = ALLOWED_TRANSITIONS[data.status]

  return (
    <section className="detail">
      <Link to="/consultations" className="back">
        ← All consultations
      </Link>

      <div className="detail__head">
        <h1>Consult #{data.id}</h1>
        <div className="badges">
          <PriorityBadge priority={data.priority} />
          <StatusBadge status={data.status} />
        </div>
      </div>

      <dl className="detail__grid">
        <div>
          <dt>Reason</dt>
          <dd>{data.reason}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{data.consultation_type.replace(/_/g, ' ')}</dd>
        </div>
        <div>
          <dt>Target specialty</dt>
          <dd>{data.target_specialty ?? '—'}</dd>
        </div>
        <div>
          <dt>Target consultant</dt>
          <dd>{data.target_consultant ?? '—'}</dd>
        </div>
        <div>
          <dt>Required response</dt>
          <dd>
            {data.required_response_minutes
              ? `${data.required_response_minutes} min`
              : '—'}
          </dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{new Date(data.created_at).toLocaleString()}</dd>
        </div>
        {data.clinical_summary && (
          <div className="detail__full">
            <dt>Clinical summary</dt>
            <dd>{data.clinical_summary}</dd>
          </div>
        )}
        {data.specific_questions && (
          <div className="detail__full">
            <dt>Specific questions</dt>
            <dd>{data.specific_questions}</dd>
          </div>
        )}
      </dl>

      <div className="actions">
        <h2>Workflow</h2>
        {nextStates.length === 0 ? (
          <p className="muted">This consultation is in a terminal state.</p>
        ) : (
          <div className="action-buttons">
            {nextStates.map((s) => (
              <button
                key={s}
                className="btn btn--outline"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate(s)}
              >
                {s.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        )}
        {mutation.isError && (
          <p className="error">{(mutation.error as Error).message}</p>
        )}
      </div>

      <div className="timeline">
        <h2>Audit timeline</h2>
        <ol>
          {data.events.map((ev) => (
            <li key={ev.id}>
              <span className="timeline__dot" />
              <div>
                <strong>
                  {ev.from_status ? `${ev.from_status} → ` : ''}
                  {ev.to_status}
                </strong>
                {ev.note && <span className="muted"> — {ev.note}</span>}
                <div className="muted small">
                  {new Date(ev.created_at).toLocaleString()}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
