# Technologies

For an understanding of the technologies and why to use each of them, this section was created for later understandings of architectural decisions.

| Technology     | Why it's being used                                                                                                    | Main advantages of choice                                                                                                                                                                         |
|----------------|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| NATS           | Real-time messaging system for communication between microservices and data streaming.                                 | Simplicity: Easy to set up and use. Performance: Very low latency for real-time events. Robustness: JetStream ensures that no critical messages are lost.                                         |
| Redis          | High-performance cache for implementing Cache-Aside Pattern, speeding up API responses.                                | Speed: Near-instantaneous memory data access. Market Standard: Ideal tool for Cache-Aside pattern. Flexibility: Supports multiple complex data structures.                                        |
| PostgreSQL     | Main relational database to store data of emotions, transactions, credits, etc.                                        | Reliability: ACID compliance ensures data integrity. Advanced Features: JSONB support and complex queries. Extensibility: Highly customizable for future needs.                                   |
| Grafana k6     | Load testing tool and simulation of sending emotional data from the mobile app to the system and sending transactions. | Easy to Use: Scripts in JavaScript, accessible to programmers. Visualization: Native integration with Grafana for analysis of results.                                                            |
| FastAPI        | Web framework to build the system REST API quickly and efficiently.                                                    | Performance: One of the fastest Python frameworks on the market. Productivity: Automatic generation of documentation and data validation. Modernity: Native support for asynchronous programming. |
| Docker         | Containerization platform to package services, ensuring consistency between development and production environments.   | Portability: "Works on my machine" turns "works anywhere". Insulation: Each service runs in its own safe environment. Ecosystem: Wide range of tools and ready-made images.                       |
| GitHub Actions | CI/CD platform to automate release generation and publication of Docker images.                                        | Integration: Native to GitHub, making setup easier. Flexibility: Allows the creation of complex and customized workflows. Automation: Ensures a standardized and reliable deployment process.     |

## Key Concepts

**Cache-Aside pattern:** A caching strategy where the application first attempts to retrieve data from the cache. If the data is not there (cache miss), the application retrieves the data from the primary source (database), stores it in the cache, and then returns it. In this project, this pattern is being implemented with Redis.

**Circuit Breaker:** A software design pattern used to detect failures and prevent a failure in one service from spreading to others, improving system resilience. In this project, it is being implemented using the `pybreak` library.

**Event-Driven:** An architectural approach where services communicate through events instead of direct synchronous calls. Producers publish events to a message broker, and consumers react to them asynchronously. In this project, NATS is used as the messaging system to ingest emotional data streams and trigger credit evaluation workflows.

**Microservice-Based:** A software architecture style where the system is built as a collection of small, independent services that communicate with each other. Each service is responsible for a specific business capability and can be developed, deployed, and scaled independently. In this project, services for emotion ingestion, credit evaluation, and offer management follow this principle.
