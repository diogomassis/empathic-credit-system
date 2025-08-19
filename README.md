# The Empathic Credit System (ECS)

This repository contains the implementation of the Empathetic Credit System (ECS), a conceptual project that offers personalized credit offers based on the analysis of emotional and financial data. To view details of the challenge, access the [technical case details](./.github/md/technical-case.md).

**_During documentation, GIFs showing the execution of specific commands will be made available when necessary._**

## Step by step

To gain a deeper understanding of how the system execution process works, watch the video located in the video folder. [Watch the system execution process video](./video/README.md).

## Project Details

For a comprehensive understanding of the project, refer to the [Details](./.github/md/sections/details.md).

## Overview

This project implements the Empathic Credit System (ECS), a backend solution developed in response to CloudWalk's Technical Challenge. The system is designed to process users' emotional and financial data in real time, using it to calculate and offer personalized credit limits. The architecture is **microservices-based** and **event-driven**, starting with the consumption of a simulated emotional data stream via NATS.

This data, combined with the user's financial history stored in a PostgreSQL database, is used to feed a (mocked) machine learning model that assesses credit risk. Based on the risk score, the system determines the approval, limit, and interest rate of the credit. A REST API, developed in Python with FastAPI, exposes endpoints for querying credit offers and for system health checks (`/healthz`).

The approval and notification process is managed asynchronously, ensuring a fast user experience. To further enhance scalability and resilience, the system implements a **Cache-Aside pattern** with Redis to optimize query performance and a **Circuit Breaker** to protect against failures in the machine learning service. The project also incorporates best practices for observability, with structured logging, and security, such as configuration management by environment variables and API authentication.

The entire solution is containerized with Docker and orchestrated via docker-compose to facilitate the configuration and execution of the development environment.

_**All Docker images created from each service were generated via GitHub Actions and are available in the packages section of the project repository.**_

## Disclaimer

The Empathic Credit System (ECS) described in this repository is entirely fictional.  The idea of using emotional data for credit decisions was created solely for this technical challenge and does not represent any real technology.
