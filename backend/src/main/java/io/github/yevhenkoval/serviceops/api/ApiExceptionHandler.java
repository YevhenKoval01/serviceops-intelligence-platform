package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.TicketNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import java.net.URI;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(TicketNotFoundException.class)
    ResponseEntity<ProblemDetail> notFound(TicketNotFoundException exception, HttpServletRequest request) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, exception.getMessage());
        problem.setTitle("Ticket not found");
        problem.setType(URI.create("https://serviceops.local/problems/ticket-not-found"));
        problem.setInstance(URI.create(request.getRequestURI()));
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ProblemDetail> validation(MethodArgumentNotValidException exception, HttpServletRequest request) {
        Map<String, String> errors = exception.getBindingResult().getFieldErrors().stream()
                .collect(Collectors.toMap(
                        error -> error.getField(),
                        error -> error.getDefaultMessage() == null ? "Invalid value" : error.getDefaultMessage(),
                        (first, ignored) -> first
                ));
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST,
                "One or more request fields are invalid"
        );
        problem.setTitle("Validation failed");
        problem.setType(URI.create("https://serviceops.local/problems/validation"));
        problem.setInstance(URI.create(request.getRequestURI()));
        problem.setProperty("errors", errors);
        return ResponseEntity.badRequest().body(problem);
    }
}
