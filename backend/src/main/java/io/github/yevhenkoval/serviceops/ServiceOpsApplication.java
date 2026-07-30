package io.github.yevhenkoval.serviceops;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafka;

@EnableKafka
@SpringBootApplication
public class ServiceOpsApplication {

    public static void main(String[] args) {
        SpringApplication.run(ServiceOpsApplication.class, args);
    }
}
