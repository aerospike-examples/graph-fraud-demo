# Local Setup for Development and Testing

If you want to get on the ground running, this doc will have the app started in 3 easy steps.

`Requires:

- npm
- node.js
- java 21
- maven
- docker
  `

1. Start Aerospike Graph Service and Aerospike DB

```bash
docker compose up -d 
```

2. Start the Backend

```
cd java-backend
mvn spring-boot:run
```

3. Start the Frontend

```
cd frontend
npm run dev
```

or prod like:

```
cd frontend
npm run prod
```

That's it!
Navigate to the address outputted in the frontend startup, and your app will be ready!