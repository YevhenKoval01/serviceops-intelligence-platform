package io.github.yevhenkoval.serviceops.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(
        prefix = "serviceops.topics",
        name = "manage",
        havingValue = "true",
        matchIfMissing = true
)
public class KafkaTopicConfiguration {

    @Bean
    NewTopic ticketCreatedTopic(@Value("${serviceops.topics.ticket-created}") String name) {
        return new NewTopic(name, 1, (short) 1);
    }

    @Bean
    NewTopic predictionCompletedTopic(@Value("${serviceops.topics.prediction-completed}") String name) {
        return new NewTopic(name, 1, (short) 1);
    }

    @Bean
    NewTopic invalidTopic(@Value("${serviceops.topics.invalid}") String name) {
        return new NewTopic(name, 1, (short) 1);
    }
}
