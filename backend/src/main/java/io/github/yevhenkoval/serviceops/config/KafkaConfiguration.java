package io.github.yevhenkoval.serviceops.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.kafka.ConcurrentKafkaListenerContainerFactoryConfigurer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.FixedBackOff;

@Configuration
public class KafkaConfiguration {

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

    @Bean
    ConcurrentKafkaListenerContainerFactory<Object, Object> kafkaListenerContainerFactory(
            ConcurrentKafkaListenerContainerFactoryConfigurer configurer,
            ConsumerFactory<Object, Object> consumerFactory,
            KafkaTemplate<String, String> kafkaTemplate,
            @Value("${serviceops.topics.invalid}") String invalidTopic
    ) {
        var factory = new ConcurrentKafkaListenerContainerFactory<Object, Object>();
        configurer.configure(factory, consumerFactory);
        var errorHandler = new DefaultErrorHandler(
                (record, exception) -> {
                    String payload = record.value() == null ? "" : record.value().toString();
                    kafkaTemplate
                            .send(invalidTopic, record.key() == null ? null : record.key().toString(), payload)
                            .join();
                },
                new FixedBackOff(500L, 2L)
        );
        factory.setCommonErrorHandler(errorHandler);
        return factory;
    }
}
