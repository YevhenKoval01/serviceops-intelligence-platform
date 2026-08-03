package io.github.yevhenkoval.serviceops.config;

import io.github.yevhenkoval.serviceops.event.InvalidEventPublisher;
import org.apache.kafka.clients.admin.Admin;
import org.springframework.boot.autoconfigure.kafka.ConcurrentKafkaListenerContainerFactoryConfigurer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.FixedBackOff;

@Configuration
public class KafkaConfiguration {

    @Bean(destroyMethod = "close")
    Admin kafkaAdminClient(KafkaAdmin kafkaAdmin) {
        return Admin.create(kafkaAdmin.getConfigurationProperties());
    }

    @Bean
    ConcurrentKafkaListenerContainerFactory<Object, Object> kafkaListenerContainerFactory(
            ConcurrentKafkaListenerContainerFactoryConfigurer configurer,
            ConsumerFactory<Object, Object> consumerFactory,
            InvalidEventPublisher invalidEventPublisher
    ) {
        var factory = new ConcurrentKafkaListenerContainerFactory<Object, Object>();
        configurer.configure(factory, consumerFactory);
        var errorHandler = new DefaultErrorHandler(
                invalidEventPublisher::publish,
                new FixedBackOff(500L, 2L)
        );
        factory.setCommonErrorHandler(errorHandler);
        return factory;
    }
}
