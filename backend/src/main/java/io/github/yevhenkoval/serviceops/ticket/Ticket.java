package io.github.yevhenkoval.serviceops.ticket;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "tickets")
public class Ticket {

    @Id
    private UUID id;

    @Column(nullable = false, length = 150)
    private String title;

    @Column(nullable = false, length = 4000)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private TicketStatus status;

    @Enumerated(EnumType.STRING)
    @Column(name = "reported_priority", length = 16)
    private Priority reportedPriority;

    @Enumerated(EnumType.STRING)
    @Column(name = "predicted_priority", length = 16)
    private Priority predictedPriority;

    @Column(name = "predicted_category", length = 32)
    private String predictedCategory;

    @Column(name = "prediction_confidence", precision = 6, scale = 5)
    private BigDecimal predictionConfidence;

    @Column(name = "model_version", length = 64)
    private String modelVersion;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Version
    @Column(nullable = false)
    private long version;

    protected Ticket() {
    }

    public Ticket(UUID id, String title, String description, Priority reportedPriority, Instant now) {
        this.id = id;
        this.title = title;
        this.description = description;
        this.reportedPriority = reportedPriority;
        this.status = TicketStatus.OPEN;
        this.createdAt = now;
        this.updatedAt = now;
    }

    public void updateStatus(TicketStatus nextStatus, Instant now) {
        this.status = nextStatus;
        this.updatedAt = now;
    }

    public void applyPrediction(
            String category,
            Priority priority,
            BigDecimal confidence,
            String modelVersion,
            Instant now
    ) {
        this.predictedCategory = category;
        this.predictedPriority = priority;
        this.predictionConfidence = confidence;
        this.modelVersion = modelVersion;
        this.updatedAt = now;
    }

    public UUID getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public TicketStatus getStatus() {
        return status;
    }

    public Priority getReportedPriority() {
        return reportedPriority;
    }

    public Priority getPredictedPriority() {
        return predictedPriority;
    }

    public String getPredictedCategory() {
        return predictedCategory;
    }

    public BigDecimal getPredictionConfidence() {
        return predictionConfidence;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public long getVersion() {
        return version;
    }
}
