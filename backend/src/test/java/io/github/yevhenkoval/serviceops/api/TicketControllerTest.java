package io.github.yevhenkoval.serviceops.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.github.yevhenkoval.serviceops.ticket.Ticket;
import io.github.yevhenkoval.serviceops.ticket.TicketNotFoundException;
import io.github.yevhenkoval.serviceops.ticket.TicketService;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(TicketController.class)
class TicketControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TicketService ticketService;

    @Test
    void rejectsInvalidTicket() throws Exception {
        mockMvc.perform(post("/api/tickets")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "bad",
                                  "description": "short"
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Validation failed"))
                .andExpect(jsonPath("$.errors.title").exists())
                .andExpect(jsonPath("$.errors.description").exists());
    }

    @Test
    void trimsInputBeforeValidationAndCreation() throws Exception {
        UUID ticketId = UUID.randomUUID();
        when(ticketService.create(any())).thenReturn(new Ticket(
                ticketId,
                "Valid title",
                "Detailed description",
                null,
                Instant.parse("2026-07-30T10:00:00Z")
        ));

        mockMvc.perform(post("/api/tickets")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "  Valid title  ",
                                  "description": "  Detailed description  "
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(ticketId.toString()));

        ArgumentCaptor<CreateTicketRequest> request = ArgumentCaptor.forClass(CreateTicketRequest.class);
        verify(ticketService).create(request.capture());
        assertThat(request.getValue().title()).isEqualTo("Valid title");
        assertThat(request.getValue().description()).isEqualTo("Detailed description");
    }

    @Test
    void rejectsUnsupportedStatusAsProblemDetail() throws Exception {
        mockMvc.perform(patch("/api/tickets/{id}/status", UUID.randomUUID())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"status": "WAITING"}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Malformed request"))
                .andExpect(jsonPath("$.type")
                        .value("https://serviceops.local/problems/malformed-request"));
    }

    @Test
    void returnsProblemDetailForMissingTicket() throws Exception {
        UUID ticketId = UUID.randomUUID();
        when(ticketService.get(ticketId)).thenThrow(new TicketNotFoundException(ticketId));

        mockMvc.perform(get("/api/tickets/{id}", ticketId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Ticket not found"))
                .andExpect(jsonPath("$.instance").value("/api/tickets/" + ticketId));
    }

    @Test
    void rejectsMalformedTicketIdAsProblemDetail() throws Exception {
        mockMvc.perform(get("/api/tickets/not-a-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Invalid request parameter"));
    }
}
