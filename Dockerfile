# --- Java builder ---
FROM --platform=linux/amd64 amazon/aws-lambda-java:8.al2 AS java-builder

# Embulk version
ARG embulk_version=0.11.0

# Copy embulk.properties only
COPY embulk.properties /embulk/
RUN mkdir -p /embulk/bin/

# Install packages
RUN yum install -y wget curl && yum clean all

# Download embulk and jruby (using stable JRuby 9.3.10.0 due to gem install timeout issues with 9.4.x)
RUN wget -O /embulk/bin/embulk https://github.com/embulk/embulk/releases/download/v${embulk_version}/embulk-${embulk_version}.jar
RUN wget -O /embulk/bin/jruby https://repo1.maven.org/maven2/org/jruby/jruby-complete/9.3.10.0/jruby-complete-9.3.10.0.jar

# Download PostgreSQL JDBC Driver (for SCRAM-SHA-256 support) - Updated to latest version
RUN wget -O /embulk/postgresql-42.7.7.jar https://jdbc.postgresql.org/download/postgresql-42.7.7.jar

# Install embulk gem
RUN java -jar /embulk/bin/embulk -X embulk_home=/embulk gem install embulk -v ${embulk_version} -N

# Install gems
RUN java -jar /embulk/bin/embulk -X embulk_home=/embulk gem install \
    msgpack \
    liquid \
    -N

# Install plugins
RUN java -jar /embulk/bin/embulk -X embulk_home=/embulk gem install \
    embulk-filter-typecast \
    embulk-filter-expand_json \
    embulk-input-mysql \
    embulk-input-postgresql \
    embulk-output-redshift \
    embulk-input-mongodb \
    -N

# Copy config files
COPY config/* /embulk/config/

# --- Lambda runtime ---
FROM --platform=linux/amd64 amazon/aws-lambda-python:3.11

# Copy embulk from java-builder
COPY --from=java-builder /embulk /embulk

# Install Java runtime required for Embulk execution
RUN yum update -y && yum install -y java-1.8.0-openjdk-headless && yum clean all

# Install Python dependencies (for better Docker layer caching)
COPY src/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -t /var/task/

# Copy application code after dependencies
COPY src/main.py /var/task/

# Set working directory
WORKDIR /var/task

# Set command
CMD [ "main.lambda_handler" ]