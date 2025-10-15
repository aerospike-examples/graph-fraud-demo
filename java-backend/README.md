# Configuring Rules
Since this application uses springboot, classes tagged (annotated) with `@Service`, or `@Component`, can
have properties, and other services and components injected into their constructors.

This is also how rules work. All rules that you want to use in this run, should be tagged with `@Component`, and will
be injected into the fraud service by springboot automatically.