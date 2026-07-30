FROM maven:3.9.9-eclipse-temurin-21-alpine AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn --batch-mode dependency:go-offline
COPY src src
RUN mvn --batch-mode package -DskipTests

FROM eclipse-temurin:21.0.7_6-jre-alpine
RUN apk add --no-cache curl
WORKDIR /app
COPY --from=build /workspace/target/serviceops-backend-0.1.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
