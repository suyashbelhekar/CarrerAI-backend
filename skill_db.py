"""
Predefined skill database for multiple job roles.
"""

JOB_ROLES = {
    "Data Scientist": {
        "required_skills": [
            "python", "machine learning", "deep learning", "statistics", "sql",
            "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
            "data visualization", "matplotlib", "seaborn", "r", "spark",
            "hadoop", "tableau", "power bi", "nlp", "computer vision",
            "feature engineering", "model deployment", "docker", "git",
            "jupyter", "hypothesis testing", "regression", "classification",
            "clustering", "neural networks", "data wrangling", "etl",
            "a/b testing", "time series", "reinforcement learning"
        ],
        "core_skills": ["python", "machine learning", "statistics", "sql", "pandas"],
        "description": "Analyzes complex data to help organizations make better decisions."
    },
    "Software Engineer": {
        "required_skills": [
            "python", "java", "javascript", "typescript", "c++", "c#",
            "react", "node.js", "angular", "vue.js", "rest api", "graphql",
            "sql", "nosql", "mongodb", "postgresql", "redis", "docker",
            "kubernetes", "aws", "azure", "gcp", "git", "ci/cd",
            "microservices", "system design", "data structures", "algorithms",
            "agile", "scrum", "unit testing", "tdd", "linux", "bash",
            "html", "css", "webpack", "spring boot", "django", "fastapi"
        ],
        "core_skills": ["python", "javascript", "git", "data structures", "algorithms"],
        "description": "Designs, develops, and maintains software systems."
    },
    "Frontend Developer": {
        "required_skills": [
            "html", "css", "javascript", "typescript", "react", "vue.js",
            "angular", "tailwind css", "sass", "webpack", "vite", "git",
            "responsive design", "accessibility", "performance optimization",
            "rest api", "graphql", "redux", "zustand", "framer motion",
            "testing library", "jest", "cypress", "figma", "ui/ux",
            "cross-browser compatibility", "seo", "pwa", "web components"
        ],
        "core_skills": ["html", "css", "javascript", "react", "git"],
        "description": "Builds user interfaces and web experiences."
    },
    "Backend Developer": {
        "required_skills": [
            "python", "java", "node.js", "go", "rust", "c#",
            "rest api", "graphql", "grpc", "sql", "nosql", "postgresql",
            "mongodb", "redis", "rabbitmq", "kafka", "docker", "kubernetes",
            "aws", "azure", "microservices", "system design", "git",
            "ci/cd", "linux", "bash", "security", "authentication",
            "oauth", "jwt", "caching", "load balancing", "nginx"
        ],
        "core_skills": ["python", "sql", "rest api", "docker", "git"],
        "description": "Builds server-side logic and database management."
    },
    "DevOps Engineer": {
        "required_skills": [
            "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
            "ansible", "jenkins", "github actions", "gitlab ci", "linux",
            "bash", "python", "monitoring", "prometheus", "grafana",
            "elk stack", "nginx", "load balancing", "networking", "security",
            "ci/cd", "git", "helm", "service mesh", "istio", "vault",
            "infrastructure as code", "site reliability", "incident management"
        ],
        "core_skills": ["docker", "kubernetes", "aws", "ci/cd", "linux"],
        "description": "Manages infrastructure and deployment pipelines."
    },
    "Machine Learning Engineer": {
        "required_skills": [
            "python", "machine learning", "deep learning", "tensorflow", "pytorch",
            "scikit-learn", "mlops", "docker", "kubernetes", "aws", "azure",
            "model deployment", "model monitoring", "feature engineering",
            "data pipelines", "spark", "sql", "git", "ci/cd",
            "neural networks", "transformers", "hugging face", "onnx",
            "triton", "kubeflow", "mlflow", "airflow", "dvc", "ray"
        ],
        "core_skills": ["python", "machine learning", "tensorflow", "docker", "mlops"],
        "description": "Builds and deploys ML models at scale."
    },
    "Product Manager": {
        "required_skills": [
            "product strategy", "roadmap planning", "agile", "scrum",
            "user research", "data analysis", "sql", "a/b testing",
            "stakeholder management", "communication", "jira", "confluence",
            "figma", "market research", "competitive analysis", "kpis",
            "okrs", "prioritization", "user stories", "wireframing",
            "go-to-market", "pricing strategy", "customer development"
        ],
        "core_skills": ["product strategy", "agile", "data analysis", "communication", "user research"],
        "description": "Defines product vision and drives execution."
    },
    "Cybersecurity Analyst": {
        "required_skills": [
            "network security", "penetration testing", "vulnerability assessment",
            "siem", "incident response", "threat intelligence", "python",
            "linux", "bash", "firewalls", "ids/ips", "encryption",
            "pki", "oauth", "zero trust", "compliance", "iso 27001",
            "soc 2", "gdpr", "ethical hacking", "kali linux", "metasploit",
            "wireshark", "nmap", "burp suite", "forensics", "malware analysis"
        ],
        "core_skills": ["network security", "penetration testing", "linux", "python", "incident response"],
        "description": "Protects systems and networks from cyber threats."
    }
}

COURSE_RECOMMENDATIONS = {
    "python": [
        {"title": "Python for Everybody", "platform": "Coursera", "url": "https://www.coursera.org/specializations/python", "level": "Beginner"},
        {"title": "Complete Python Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/complete-python-bootcamp/", "level": "Beginner"}
    ],
    "machine learning": [
        {"title": "Machine Learning Specialization", "platform": "Coursera", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "level": "Intermediate"},
        {"title": "Fast.ai Practical Deep Learning", "platform": "Fast.ai", "url": "https://course.fast.ai/", "level": "Intermediate"}
    ],
    "deep learning": [
        {"title": "Deep Learning Specialization", "platform": "Coursera", "url": "https://www.coursera.org/specializations/deep-learning", "level": "Advanced"},
        {"title": "PyTorch for Deep Learning", "platform": "Udemy", "url": "https://www.udemy.com/course/pytorch-for-deep-learning/", "level": "Intermediate"}
    ],
    "react": [
        {"title": "React - The Complete Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/", "level": "Intermediate"},
        {"title": "Full Stack Open", "platform": "University of Helsinki", "url": "https://fullstackopen.com/", "level": "Intermediate"}
    ],
    "docker": [
        {"title": "Docker & Kubernetes: The Practical Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/", "level": "Intermediate"},
        {"title": "Docker Official Docs", "platform": "Docker", "url": "https://docs.docker.com/get-started/", "level": "Beginner"}
    ],
    "sql": [
        {"title": "SQL for Data Science", "platform": "Coursera", "url": "https://www.coursera.org/learn/sql-for-data-science", "level": "Beginner"},
        {"title": "Mode SQL Tutorial", "platform": "Mode", "url": "https://mode.com/sql-tutorial/", "level": "Beginner"}
    ],
    "kubernetes": [
        {"title": "Kubernetes for Developers", "platform": "Linux Foundation", "url": "https://training.linuxfoundation.org/training/kubernetes-for-developers/", "level": "Advanced"},
        {"title": "Kubernetes Crash Course", "platform": "TechWorld with Nana", "url": "https://www.youtube.com/watch?v=s_o8dwzRlu4", "level": "Beginner"}
    ],
    "aws": [
        {"title": "AWS Certified Solutions Architect", "platform": "AWS", "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/", "level": "Intermediate"},
        {"title": "AWS Cloud Practitioner", "platform": "Coursera", "url": "https://www.coursera.org/learn/aws-cloud-practitioner-essentials", "level": "Beginner"}
    ],
    "default": [
        {"title": "Search on Coursera", "platform": "Coursera", "url": "https://www.coursera.org/search?query=", "level": "Varies"},
        {"title": "Search on Udemy", "platform": "Udemy", "url": "https://www.udemy.com/courses/search/?q=", "level": "Varies"}
    ]
}

ATS_KEYWORDS = {
    "Data Scientist": ["data analysis", "predictive modeling", "statistical analysis", "machine learning algorithms", "data-driven insights"],
    "Software Engineer": ["software development lifecycle", "object-oriented programming", "scalable architecture", "code review", "technical documentation"],
    "Frontend Developer": ["responsive web design", "user interface development", "cross-browser compatibility", "performance optimization", "component-based architecture"],
    "Backend Developer": ["server-side development", "database optimization", "api development", "system architecture", "high availability"],
    "DevOps Engineer": ["infrastructure automation", "continuous integration", "continuous deployment", "cloud infrastructure", "site reliability"],
    "Machine Learning Engineer": ["model training", "model deployment", "feature engineering", "ml pipeline", "production ml systems"],
    "Product Manager": ["product lifecycle", "cross-functional collaboration", "data-driven decisions", "user-centric design", "strategic planning"],
    "Cybersecurity Analyst": ["threat detection", "security assessment", "risk management", "security protocols", "incident handling"]
}
