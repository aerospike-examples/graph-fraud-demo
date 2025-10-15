FROM maven:3.9-eclipse-temurin-21 AS build

WORKDIR /app

COPY pom.xml .
COPY mvnw .
COPY .mvn .mvn

# Download dependencies (cached if pom.xml doesn't change)
RUN chmod +x mvnw && ./mvnw dependency:go-offline -B

COPY src ./src

RUN ./mvnw clean package -DskipTests

FROM eclipse-temurin:21-jre

ENV GRAPH_HOST_ADDRESS="asgraph-service"

WORKDIR /app

COPY --from=build /app/target/fraud-detection-backend-0.0.1-SNAPSHOT.jar app.jar

CMD ["java", "-jar", "app.jar"]