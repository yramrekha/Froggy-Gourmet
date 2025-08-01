# Froggy-Gourmet
To automate client orders and quote generation
Project Summary

The objective of this project is to automate and streamline the generation of purchase orders by processing product order data from multiple sources — including manual inputs and automated exports.

The solution includes the following key components:
	•	Standardizing product data (e.g., product names, IDs, and comments) into a unified format and language (French).
	•	Matching products against a centralized master table stored in an Azure SQL Database, which includes all product information, pricing, and supplier mapping.
	•	Generating purchase orders by grouping data and applying logic based on supplier and product type.
	•	Assigning orders to the correct supplier and generating a unique internal code for each order.
	•	Supporting two primary flows:
	1.	An automated flow for handling large-scale order data.
	2.	A semi-automated UI-based flow tailored for minor loaders, enabling easier manual entry and processing.
	•	Generating a code for each manual order, which is communicated to the client for reference.
	•	Integrating with Odoo, where all finalized purchase orders will be sent and managed.

Additionally, the use of third-party software and services was deliberately minimized in line with the client’s request to reduce operating costs and avoid unnecessary subscription-based tools. As such, most of the processing is done through custom scripts and internal logic, with all development handled locally.

The scripts are actively being improved as mentioned.
