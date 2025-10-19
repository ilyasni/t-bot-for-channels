# 🛠️ Scripts

This directory contains all project scripts organized by functionality.

## 📁 Structure

```
scripts/
├── README.md                    # This file
├── start_services.py            # Main service startup script
├── check_neo4j_posts.sh         # Neo4j posts verification
├── start_telethon_langchain.sh  # Telethon + LangChain startup
├── start_telethon_n8n.sh        # Telethon + n8n startup
├── test_neo4j_graphrag.sh       # Neo4j GraphRAG testing
├── test_agents_individual.py    # Individual agent testing
└── test_full_pipeline.py        # Full pipeline testing
```

## 🚀 Quick Start Scripts

### **Main Services**
```bash
# Start all services
python3 scripts/start_services.py

# Start with specific profiles
python3 scripts/start_services.py --profile langfuse,neo4j,monitoring
```

### **Telethon Services**
```bash
# Start Telethon with LangChain
bash scripts/start_telethon_langchain.sh

# Start Telethon with n8n
bash scripts/start_telethon_n8n.sh
```

## 🧪 Testing Scripts

### **Neo4j Testing**
```bash
# Test Neo4j GraphRAG functionality
bash scripts/test_neo4j_graphrag.sh

# Check Neo4j posts
bash scripts/check_neo4j_posts.sh
```

### **Agent Testing**
```bash
# Test individual agents
python3 scripts/test_agents_individual.py

# Test full pipeline
python3 scripts/test_full_pipeline.py
```

## 📋 Script Categories

### **Service Management**
- `start_services.py` - Main orchestration script
- `start_telethon_*.sh` - Telethon service variants

### **Testing & Verification**
- `test_*.py` - Python test scripts
- `test_*.sh` - Shell test scripts
- `check_*.sh` - Verification scripts

### **Development Tools**
- All scripts support `--help` for usage information
- Scripts are designed to be run from project root
- Use `bash` for shell scripts, `python3` for Python scripts

## 🔧 Usage Examples

### **Start Services with Profiles**
```bash
# Start with monitoring
python3 scripts/start_services.py --profile monitoring

# Start with Langfuse
python3 scripts/start_services.py --profile langfuse

# Start with multiple profiles
python3 scripts/start_services.py --profile langfuse,neo4j,monitoring
```

### **Test Neo4j Integration**
```bash
# Full Neo4j test
bash scripts/test_neo4j_graphrag.sh

# Quick Neo4j check
bash scripts/check_neo4j_posts.sh
```

### **Development Testing**
```bash
# Test individual components
python3 scripts/test_agents_individual.py

# Test complete pipeline
python3 scripts/test_full_pipeline.py
```

## 📝 Notes

- All scripts are executable and include help documentation
- Scripts are designed to work with Docker Compose
- Use `--help` flag for detailed usage information
- Scripts assume proper environment setup (see main README.md)
