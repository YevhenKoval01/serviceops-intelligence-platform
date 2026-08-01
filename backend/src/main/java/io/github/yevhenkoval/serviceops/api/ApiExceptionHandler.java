package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.TicketNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import java.net.URI;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(BadCredentialsException.class)
    ResponseEntity<ProblemDetail> invalidCredentials(HttpServletRequest request) {
        return response(
                HttpStatus.UNAUTHORIZED,
                "Sign-in failed",
                "The username or password is incorrect",
                "invalid-credentials",
                request
        );
    }

    @ExceptionHandler(TicketNotFoundException.class)
    ResponseEntity<ProblemDetail> notFound(TicketNotFoundException exception, HttpServletRequest request) {
        return response(
                HttpStatus.NOT_FOUND,
                "Ticket not found",
                exception.getMessage(),
                "ticket-not-found",
                request
        );
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ProblemDetail> validation(MethodArgumentNotValidException exception, HttpServletRequest request) {
        Map<String, String> errors = exception.getBindingResult().getFieldErrors().stream()
                .collect(Collectors.toMap(
                        error -> error.getField(),
                        error -> error.getDefaultMessage() == null ? "Invalid value" : error.getDefaultMessage(),
                        (first, ignored) -> first
                ));
        ResponseEntity<ProblemDetail> response = response(
                HttpStatus.BAD_REQUEST,
                "Validation failed",
                "One or more request fields are invalid",
                "validation",
                request
        );
        response.getBody().setProperty("errors", errors);
        return response;
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ProblemDetail> unreadableRequest(HttpServletRequest request) {
        return response(
                HttpStatus.BAD_REQUEST,
                "Malformed request",
                "The request body is missing or contains unsupported JSON values",
                "malformed-request",
                request
        );
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ProblemDetail> invalidPath(HttpServletRequest request) {
        return response(
                HttpStatus.BAD_REQUEST,
                "Invalid request parameter",
                "A path or query parameter has an unsupported format",
                "invalid-parameter",
                request
        );
    }

    @ExceptionHandler(OptimisticLockingFailureException.class)
    ResponseEntity<ProblemDetail> concurrentUpdate(HttpServletRequest request) {
        return response(
                HttpStatus.CONFLICT,
                "Ticket changed",
                "The ticket was changed by another request; reload it and try again",
                "concurrent-update",
                request
        );
    }

    private ResponseEntity<ProblemDetail> response(
            HttpStatus status,
            String title,
            String detail,
            String type,
            HttpServletRequest request
    ) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setTitle(title);
        problem.setType(URI.create("https://serviceops.local/problems/" + type));
        problem.setInstance(URI.create(request.getRequestURI()));
        return ResponseEntity.status(status).body(problem);
    }
}
