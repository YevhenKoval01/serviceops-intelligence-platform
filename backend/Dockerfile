FROM maven:3.9.9-eclipse-temurin-21-alpine AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn --batch-mode dependency:go-offline
COPY src src
RUN mvn --batch-mode package -DskipTests

FROM eclipse-temurin:21.0.11_10-jre-alpine-3.23
ARG OTEL_JAVA_AGENT_VERSION=2.28.1
ARG OTEL_JAVA_AGENT_SHA256=faa89bdeebf9b1f52be4a4374689176717b02a59df2d8f8b6eb9aa39f9292589
RUN addgroup -S -g 10001 serviceops \
    && adduser -S -D -H -u 10001 -G serviceops serviceops \
    && apk add --no-cache curl \
    && curl --fail --location --silent --show-error \
        --output /opt/opentelemetry-javaagent.jar \
        "https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v${OTEL_JAVA_AGENT_VERSION}/opentelemetry-javaagent.jar" \
    && echo "${OTEL_JAVA_AGENT_SHA256}  /opt/opentelemetry-javaagent.jar" \
        | sha256sum -c -
WORKDIR /app
COPY --from=build --chown=10001:10001 /workspace/target/serviceops-backend-0.1.0.jar app.jar
ENV JAVA_TOOL_OPTIONS="-javaagent:/opt/opentelemetry-javaagent.jar" \
    OTEL_SDK_DISABLED=true
EXPOSE 8080
USER 10001:10001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
