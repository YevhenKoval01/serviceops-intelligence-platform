with lifecycle as (
    select
        ticket_id,
        min(occurred_at) filter (
            where current_status <> 'OPEN' and event_type <> 'MIGRATED'
        ) as exact_first_response_at,
        max(occurred_at) filter (
            where current_status = 'RESOLVED' and event_type <> 'MIGRATED'
        ) as exact_latest_resolution_at,
        count(*) filter (where event_type = 'REOPENED') as reopen_count,
        bool_or(event_type = 'MIGRATED') as has_migrated_snapshot
    from {{ ref('fct_ticket_lifecycle_events') }}
    group by ticket_id
), enriched as (
    select
        ticket.ticket_id,
        ticket.status,
        ticket.effective_priority,
        ticket.category,
        ticket.created_at,
        ticket.updated_at,
        case
            when lifecycle.has_migrated_snapshot and ticket.status <> 'OPEN'
                then ticket.updated_at
            else lifecycle.exact_first_response_at
        end as first_response_at,
        case
            when ticket.status <> 'RESOLVED' then null
            when lifecycle.has_migrated_snapshot then ticket.updated_at
            else lifecycle.exact_latest_resolution_at
        end as resolved_at,
        coalesce(lifecycle.reopen_count, 0) as reopen_count,
        case
            when lifecycle.has_migrated_snapshot then 'MIGRATED_SNAPSHOT'
            else 'EXACT'
        end as history_quality,
        ticket.created_at
            + policy.first_response_target_minutes * interval '1 minute'
            as first_response_due_at,
        ticket.created_at
            + policy.resolution_target_minutes * interval '1 minute'
            as resolution_due_at
    from {{ ref('stg_tickets') }} as ticket
    inner join {{ ref('sla_policies') }} as policy
        on ticket.effective_priority = policy.priority
    left join lifecycle
        on ticket.ticket_id = lifecycle.ticket_id
)
select
    ticket_id,
    status,
    effective_priority,
    category,
    created_at,
    created_at::date as created_date,
    updated_at,
    first_response_at,
    resolved_at,
    first_response_due_at,
    resolution_due_at,
    extract(epoch from first_response_at - created_at) / 60.0 as first_response_minutes,
    extract(epoch from resolved_at - created_at) / 60.0 as resolution_minutes,
    case
        when status <> 'RESOLVED'
            then greatest(0, extract(epoch from current_timestamp - created_at) / 60.0)
        else null
    end as backlog_age_minutes,
    case
        when first_response_at is null then null
        else first_response_at <= first_response_due_at
    end as first_response_sla_met,
    case
        when resolved_at is null then null
        else resolved_at <= resolution_due_at
    end as resolution_sla_met,
    status <> 'RESOLVED' and current_timestamp > resolution_due_at as is_breached_backlog,
    status <> 'RESOLVED' as is_open_backlog,
    reopen_count,
    reopen_count > 0 as was_reopened,
    history_quality
from enriched
