provider "aws" {
  region = "us-east-1" # Change to your preferred region
}

# 1. Variables for Easy Customization
variable "my_ip" {
  type        = string
  description = "Your public IP address in CIDR notation (e.g., '192.0.2.1/32')"
  default     = "{Your public ip here}"
}

variable "existing_key_name" {
  type        = string
  description = "The name of the SSH key pair already created in AWS"
  default     = "{Key pair name here}"
}

variable "existing_bucket_name" {
  type        = string
  description = "The name of your existing S3 bucket"
  default     = "{Bucket name}"
}

# 2. VPC & Networking Setup
resource "aws_vpc" "public_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "public-vpc"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.public_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true # Ensures EC2 gets a public IP
  availability_zone       = "us-east-1a"

  tags = {
    Name = "public-subnet"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.public_vpc.id

  tags = {
    Name = "vpc-igw"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.public_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "public-route-table"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

# 3. Security Group (Restricted SSH)
resource "aws_security_group" "ec2_sg" {
  name        = "allow_ssh_my_ip"
  description = "Allow SSH inbound traffic from my IP only"
  vpc_id      = aws_vpc.public_vpc.id

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ec2-ssh-sg"
  }
}

# 4. IAM Role and Policy for S3 Access
resource "aws_iam_role" "ec2_role" {
  name = "ec2_s3_read_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "s3_read_policy" {
  name        = "ec2_s3_bucket_read_policy"
  description = "Allows ListBucket and GetObject on a specific bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = ["arn:aws:s3:::${var.existing_bucket_name}"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["arn:aws:s3:::${var.existing_bucket_name}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "role_policy_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_read_policy.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2_s3_instance_profile"
  role = aws_iam_role.ec2_role.name
}

# 5. Fetch Latest Ubuntu 26.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

# 6. EC2 Instance Configuration
resource "aws_instance" "web_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  root_block_device {
    volume_size           = 45    # Size in GiB
    volume_type           = "gp3" # General Purpose SSD
    delete_on_termination = true  # Automatically cleans up volume when instance is deleted
  }
  # Existing Key Pair Name
  key_name = var.existing_key_name

  # Attach the IAM Instance Profile
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  # Download configuration scripts from github
  user_data = <<-EOF
    #!/bin/bash
    cd /home/ubuntu

    sudo curl -O https://raw.githubusercontent.com/Seth-Wr/Serverless_Splunk_Lab/main/splunk/scripts/Splunk_Lab_Setup.sh
    
    sudo curl -O https://raw.githubusercontent.com/Seth-Wr/Serverless_Splunk_Lab/main/splunk/scripts/alert_setup.sh
  
    sudo curl -O https://raw.githubusercontent.com/Seth-Wr/Serverless_Splunk_Lab/main/splunk/scripts/dashboard_setup.sh
    EOF

  tags = {
    Name = "S3-Reader-Instance"
  }
}

# 7. Outputs
output "instance_public_ip" {
  value       = "ssh -L 8000:localhost:8000 -i your_key_name ubuntu@${aws_instance.web_server.public_ip} and once inside to startup splunk enviroment run sudo bash ./Splunk_Lab_Setup.sh && sudo bash ./alert_setup.sh && sudo bash ./dashboard_setup.sh"
  description = "The public IP address of your EC2 instance and start setup commands"
}
