FROM eclipse-temurin:21-jdk AS build
WORKDIR /app

COPY . .

RUN chmod +x gradlew \
 && sed -i 's/\r$//' gradlew \
 && ./gradlew clean bootWar

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

COPY --from=build /app/build/libs/*.war app.war

EXPOSE 8080
CMD ["java","-jar","app.war"]
