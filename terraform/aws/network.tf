resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  for_each = toset(local.azs)

  vpc_id                  = aws_vpc.main.id
  availability_zone       = each.value
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, index(local.azs, each.value))
  map_public_ip_on_launch = true

  tags = { Name = "${local.name_prefix}-public-${each.value}" }
}

resource "aws_subnet" "app" {
  for_each = toset(local.azs)

  vpc_id            = aws_vpc.main.id
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, index(local.azs, each.value) + 4)

  tags = { Name = "${local.name_prefix}-app-${each.value}" }
}

resource "aws_subnet" "database" {
  for_each = toset(local.azs)

  vpc_id            = aws_vpc.main.id
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, index(local.azs, each.value) + 8)

  tags = { Name = "${local.name_prefix}-database-${each.value}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  for_each = toset(local.azs)

  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  for_each = toset(local.azs)

  allocation_id = aws_eip.nat[each.value].id
  subnet_id     = aws_subnet.public[each.value].id

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "app" {
  for_each = toset(local.azs)

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[each.value].id
  }
}

resource "aws_route_table_association" "app" {
  for_each = toset(local.azs)

  subnet_id      = aws_subnet.app[each.value].id
  route_table_id = aws_route_table.app[each.value].id
}
