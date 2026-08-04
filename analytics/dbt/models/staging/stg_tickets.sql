select
    id as ticket_id,
    title,
    description,
    status,
    reported_priority,
    predicted_priority,
    coalesce(reported_priority, predicted_priority, 'MEDIUM') as effective_priority,
    coalesce(predicted_category, 'unclassified') as category,
    prediction_confidence,
    model_version,
    created_at,
    updated_at
from {{ source('serviceops', 'tickets') }}
