#!/bin/bash
: '
Date: 2025-11-13

List resources for providers that 
are reported as candidates
for allocating a given flavor, 
according to Placement.

The scipt lists for each candidate:

* Inventory with correcting for overcommit (openstack allocation candidate list ...)

* Inventory without correcting for overcommit (openstack resource provider inventory list ...)

* The command for listing existing allocated flavors (openstack resource provider show --allocations ...)

limit:
N: List up to N candidates
-1: List all candidates

Example::
./allocation-candidate.sh m1.small
'

# Define column widths
C1_WIDTH=5
C2_WIDTH=45
C3_WIDTH=60

flavor=$1
#flavor=m1.small

limit=1

specs=$(openstack flavor show $flavor -c vcpus -c ram -c disk -f json)

vcpus=$(echo $specs | jq '.vcpus')
ram=$(echo $specs | jq '.ram')
disk=$(echo $specs | jq '.disk')

if [[ "$limit" == "-1" ]]
then
  candidates=$(openstack --os-placement-api-version 1.10 allocation candidate list --resource VCPU=$vcpus --resource MEMORY_MB=$ram --resource DISK_GB=$disk -c '#' -c 'resource provider' -c 'inventory used/capacity' -f json)
else
  candidates=$(openstack --os-placement-api-version 1.16 allocation candidate list --resource VCPU=$vcpus --resource MEMORY_MB=$ram --resource DISK_GB=$disk -c '#' -c 'resource provider' -c 'inventory used/capacity' --limit $limit -f json)
fi

echo "* Flavor $flavor with VCPU=$vcpus,MEMORY_MB=$ram,DISK_GB=$disk"

while read candidate
do
  uuid=$(echo $candidate | jq '."resource provider"' | tr -d '"')
  rank=$(echo $candidate | jq '."#"' | tr -d '"')
  inventory=$(echo $candidate | jq '."inventory used/capacity"' | tr -d '"')
  resource_provider=$(openstack resource provider show $uuid -c name -f value)

  printf "%-*s  %-*s  %-*s\n" \
    "$C1_WIDTH" "*" \
    "$C2_WIDTH" "Candidate (resource provier UUID):" \
    "$C3_WIDTH" "$uuid"

  printf "%-*s  %-*s  %-*s\n" \
    "$C1_WIDTH" "#" \
    "$C2_WIDTH" "Name" \
    "$C3_WIDTH" "Inventory used/capacity including overcommit"

  printf "%-*s  %-*s  %-*s\n" \
    "$C1_WIDTH" "$rank" \
    "$C2_WIDTH" "$resource_provider" \
    "$C3_WIDTH" "$inventory"

  echo "* Current inventory for $resource_provider"

  openstack resource provider inventory list $uuid

  echo "* Show existing allocations on $resource_provider"

  echo "openstack resource provider show --allocations $uuid -c allocations --fit-width"

done < <(echo $candidates | jq -c '.[]')

