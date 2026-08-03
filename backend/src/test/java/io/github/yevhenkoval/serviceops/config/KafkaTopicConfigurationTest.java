package io.github.yevhenkoval.serviceops.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.apache.kafka.clients.admin.NewTopic;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

class KafkaTopicConfigurationTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withUserConfiguration(KafkaTopicConfiguration.class)
            .withPropertyValues(
                    "serviceops.topics.ticket-created=created",
                    "serviceops.topics.prediction-completed=predicted",
                    "serviceops.topics.invalid=invalid"
            );

    @Test
    void createsTopicsByDefaultForLocalKafka() {
        contextRunner.run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context).getBeans(NewTopic.class).hasSize(3);
        });
    }

    @Test
    void omitsTopicAdministrationForAzureEventHubs() {
        contextRunner
                .withPropertyValues("serviceops.topics.manage=false")
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context).doesNotHaveBean(NewTopic.class);
                });
    }
}
