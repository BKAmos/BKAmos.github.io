terraform {
  required_version = ">= 1.6.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  region = var.region
}

variable "region" {
  description = "OCI region, for example us-ashburn-1."
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment OCID for all resources."
  type        = string
}

variable "availability_domain" {
  description = "Availability domain name for the Always-Free VM."
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key to install for opc."
  type        = string
}

variable "repo_url" {
  description = "Git repository URL cloned by cloud-init."
  type        = string
  default     = "https://github.com/BKAmos/BKAmos.github.io.git"
}

variable "repo_branch" {
  description = "Branch containing the DESeq workflow stack."
  type        = string
  default     = "cursor/deseq-ui-mcp-workflow-532c"
}

variable "api_token" {
  description = "Bearer token expected by the FastAPI API."
  type        = string
  sensitive   = true
}

variable "cloudflare_cidr_blocks" {
  description = "Optional CIDR blocks allowed to reach port 8000. Use Cloudflare IP ranges in production."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_vcn" "deseq" {
  compartment_id = var.compartment_ocid
  cidr_block     = "10.42.0.0/16"
  display_name   = "deseq-workflow-vcn"
  dns_label      = "deseqwf"
}

resource "oci_core_internet_gateway" "deseq" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.deseq.id
  display_name   = "deseq-workflow-igw"
  enabled        = true
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.deseq.id
  display_name   = "deseq-workflow-public-routes"

  route_rules {
    network_entity_id = oci_core_internet_gateway.deseq.id
    destination       = "0.0.0.0/0"
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.deseq.id
  display_name   = "deseq-workflow-security"

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  dynamic "ingress_security_rules" {
    for_each = var.cloudflare_cidr_blocks
    content {
      protocol = "6"
      source   = ingress_security_rules.value
      tcp_options {
        min = 8000
        max = 8000
      }
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 9000
      max = 9001
    }
  }

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.deseq.id
  cidr_block                 = "10.42.1.0/24"
  display_name               = "deseq-workflow-public-subnet"
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  prohibit_public_ip_on_vnic = false
}

locals {
  cloud_init = templatefile("${path.module}/cloud-init.yaml", {
    repo_url    = var.repo_url
    repo_branch = var.repo_branch
    api_token   = var.api_token
  })
}

resource "oci_core_instance" "deseq" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = "deseq-workflow-a1"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 2
    memory_in_gbs = 12
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    display_name     = "deseq-workflow-vnic"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(local.cloud_init)
  }
}

output "api_base_url" {
  value = "http://${oci_core_instance.deseq.public_ip}:8000"
}

output "minio_console_url" {
  value = "http://${oci_core_instance.deseq.public_ip}:9001"
}
