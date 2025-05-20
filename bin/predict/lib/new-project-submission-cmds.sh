: '
bash iaas-project-submission-cmds.sh RT SUBMISSION_ID

Suggests commands based on submission to
https://nettskjema.no/a/iaas-project (request.nrec.no)

2024-04-06 yyyy-mm-dd

export NETTSKJEMA_API_ACCESS_TOKEN=TOKEN

Tested on RT SUBMISSION_ID Summary

6165179 31215102 Virtual GPU, with HDD volume quota
6169259 31265206 Shared, with small base quota, custom HDD and SSD volume quota, and other users
6171415 31295900 Shared, with small base quota, HDD and SSD volume quota, and other user
6152187 31136398 Shared, with large base quota, custom shpc flavor, large os disk shpc quota, custom SSD volume quota, and other users
6167493 31243270 Personal, with small base quota
6167041 31235749 -"-
6152026 31134696
6156579 31167241
6132597 30982716
6150965 31122499
6152144 31136133
6147307 31095286
6570990 33117323 Share, with large base quota, custom HDD and SSH volume quota, optional contact, other users, large os disk shpc quotas
and more
'

set -e

RT=$1
SUBMISSION_ID=$2
element_data=$3
answer_data=$(curl -s -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" -X GET https://api.nettskjema.no/v3/form/submission/${SUBMISSION_ID})

echo

declare -A clues

clues[rt]=$RT
clues[submissionId]=$SUBMISSION_ID
clues[respondentEmail]=$(echo $answer_data | jq '.submissionMetadata.respondentEmail' | tr -d '"')

numAnswers=$(echo $answer_data | jq '.answers | length')
for ((i=0; i<$numAnswers; ++i))
do
  answer=$(echo $answer_data | jq ".answers[$i]")
  elementId=$(echo $answer | jq '.elementId')
  answer_elements=$(echo $element_data | jq '.[]' | jq "select(.elementId==$elementId)")
  answerOptionIds=($(echo $answer | jq '.answerOptionIds' | tr -d '[' | tr -d ']' | tr -d ' ' | tr ',' ' '))
  if [ ${#answerOptionIds[*]} -eq 0 ]
  then
    answer_text=$(echo $answer | jq '.textAnswer' | tr -d '"')
  elif [ ${#answerOptionIds[*]} -eq 1 ]
  then
    answerOptionId=${answerOptionIds[0]}
    answer_text=$(echo $answer_elements | jq '.answerOptions[]' | jq "select(.answerOptionId==$answerOptionId).text" | tr -d '"')
  else
    answer_texts=()
    for answerOptionId in ${answerOptionIds[*]}
    do
      answer_texts+=("$(echo $answer_elements | jq '.answerOptions[]' | jq "select(.answerOptionId==$answerOptionId).text" | tr -d '"')")
    done
  fi
  # Project Type
  if [[ $elementId == 4559698 ]]
  then
    clues[projectType]=$answer_text
  # Special resources
  elif [[ $elementId == 5052840 ]]
  then
    # Only one special resource
    specialResource="$answer_text"
    if [ ! -z "$specialResource" ]
    then
      if [[ $specialResource == 'Shared HPC' ]]
      then
        clues[shpcResource]=$specialResource
      elif [[ $specialResource == 'SSD Storage' ]]
      then
        clues[ssdStorageResource]=$specialResource
      fi
    # Multiple special resources
    elif [ ${#answer_texts[@]} -gt 0  ]
    then
      for specialResource in "${answer_texts[@]}"
      do
        if [[ $specialResource == 'Shared HPC' ]]
        then
          clues[shpcResource]=$specialResource
        elif [[ $specialResource == 'SSD Storage' ]]
        then
          clues[ssdStorageResource]=$specialResource
        fi
      done
    fi

  # Private project base quota
  elif [[ $elementId == 4559704 ]]
  then
    clues[personalProjectBaseQuota]=$answer_text
  # Shared project base quota
  elif [[ $elementId == 4559703 ]]
  then
    clues[sharedProjectBaseQuota]=$answer_text
  # Other sHPC flavors
  elif [[ $elementId == 5051926 ]]
  then
    otherShpcResourcesArray=()
    for otherShpcResource in "${answer_texts[@]}"
    do
      otherShpcResourcesArray+=("$otherShpcResource")
    done
    numOtherShpcResources=${#otherShpcResourcesArray[@]}
  # Project sHPC quota
  # In this script: Total project quota is the largest of base quota and sHPC quota.
  elif [[ $elementId == 5052831 ]]
  then
    clues[projectShpcQuota]=$answer_text
  # Regular volume quota for shared projects
  elif [[ $elementId == 5052835 ]] || [[ $elementId == 5052848 ]] || [[ $elementId == 6148367 ]]
  then
    clues[regularVolumeQuota]=$answer_text
  # SSD volume quota for shared projects
  elif [[ $elementId == 5052847 ]]
  then
    clues[ssdVolumeQuota]=$answer_text
  # Regular volume quota for vgpu projects
  elif [[ $elementId == 5052849 ]]
  then
    clues[regularVolumeQuota]=$answer_text
  # Optional contact
  elif [[ $elementId == 4559701 ]]
  then
    clues[optionalContact]=$answer_text
  # Project name
  elif [[ $elementId == 4559713 ]]
  then
    clues[projectName]=$answer_text
  # Project description
  elif [[ $elementId == 4559710 ]]
  then
    clues[projectDescription]=$answer_text
  # Expiration date
  elif [[ $elementId == 4559702 ]]
  then
    clues[expirationDate]=$answer_text
  # Educational institution
  elif [[ $elementId == 4559711 ]]
  then
    clues[educationalInstitution]=$answer_text
  # Project category
  elif [[ $elementId == 4559712 ]]
  then
    clues[projectCategory]=$answer_text
  # Additional users
  elif [[ $elementId == 4559714 ]]
  then
    clues[additionalUsers]=$answer_text
  # Other
  # TODO: add
  fi
done

# (info overview) print stored keys and values
for key in ${!clues[*]}
do
  value=${clues[$key]}
  #printf "%s\t%s\n" $key "$value"
  echo $key : $value
done
if [ ! -z $numOtherShpcResources ]
then
  for ((j=0; j<$numOtherShpcResources; ++j))
  do
    echo "otherShpcResource $(($j+1)) : ${otherShpcResourcesArray[$j]}"
  done
fi
echo

# Interactive if not Personal project
if [[ ${clues[projectType]} != 'Personal' ]]
then
  # project
  read -e -p "projectName (Enter to continue): " -i "${clues[projectName]}" kanswer
  clues[projectName]=$kanswer

  # description
  # Take the first sentence in projectDescription, as a start
  desc="${clues[projectDescription]}"
  desc="${desc%%.*}"
  read -e -p "projectDescription, first sentence (Enter to continue): " -i "$desc" kanswer
  clues[projectDescription]="$kanswer"

  echo
fi

# Start building cmds

# Build project.py cmd arguments

declare -A pcargs

# createArgument: project.py create or project.py create-private
# Default: create
pcargs[createArgument]=create

# Creating arguments, first for create-private, then for create

# --end
pcargs[end]=$(bash -c 'end="$(echo $0 | cut -d . -f 3)-$(echo $0 | cut -d . -f 2)-$(echo $0 | cut -d . -f 1)"; echo $end' ${clues[expirationDate]})

# -q (choose from 'small', 'medium', 'large', 'vgpu')
declare -A pquotas
# vgpu
if [[ ${clues[projectType]} == 'Virtual GPU' ]]
then
  pcargs[quota]=vgpu
# small, medium in the context of Personal project
elif [[ ${clues[projectType]} == 'Personal' ]]
then
  pcargs[createArgument]=create-private
  if [[ ${clues[personalProjectBaseQuota]} == 'Small: 5 instances, 10 cores and 16 GB RAM' ]]
  then
    pcargs[quota]=small
  elif [[ ${clues[personalProjectBaseQuota]} == 'Medium: 20 instances, 40 cores and 64 GB RAM' ]]
  then
    pcargs[quota]=medium
  fi
# small, medium, large in the context of Shared project
elif [[ ${clues[projectType]} == 'Shared' ]]
then
  # Quota (small, medium, large)
  if [[ ${clues[sharedProjectBaseQuota]} == 'Small: 5 instances, 10 cores and 16 GB RAM' ]]
  then
    pcargs[quota]=small
    pquotas[instances]=5
    pquotas[cores]=10
    pquotas[ram]=$((1024*16))
  elif [[ ${clues[sharedProjectBaseQuota]} == 'Medium: 20 instances, 40 cores and 64 GB RAM' ]]
  then
    pcargs[quota]=medium
    pquotas[instances]=20
    pquotas[cores]=40
    pquotas[ram]=$((1024*64))
  elif [[ ${clues[sharedProjectBaseQuota]} == 'Large: 50 instances, 100 cores and 96 GB RAM' ]]
  then
    pcargs[quota]=large
    pquotas[instances]=50
    pquotas[cores]=100
    pquotas[ram]=$((1024*96))
  fi
fi

# --rt
pcargs[rt]=${clues[rt]}

# institution and region specific options
if [[ ${clues[educationalInstitution]} == 'University of Oslo (UiO)' ]]
then
  # May need to shorten UiO E-mail to <username>@uio.no. The correct shortened UiO E-mail may be found using bofh on the submitted UiO E-mail in the form.
  # user (create-private)
  pcargs[user]=${clues[respondentEmail]}
  # --region (create)
  pcargs[region]=osl
  # -a (create)
  pcargs[admin]=${clues[respondentEmail]}
  # -o (choose from 'nrec', 'uio', 'uib', 'uit', 'ntnu', 'nmbu', 'vetinst', 'hvl')
  pcargs[org]=uio
elif [[ ${clues[educationalInstitution]} == 'University of Bergen (UiB)' ]]
then
  # user (create-private)
  pcargs[user]=${clues[respondentEmail]}
  # --region (create)
  pcargs[region]=bgo
  # -a (create)
  pcargs[admin]=${clues[respondentEmail]}
  # -o (choose from 'nrec', 'uio', 'uib', 'uit', 'ntnu', 'nmbu', 'vetinst', 'hvl')
  pcargs[org]=uib
else
  # user (create-private)
  pcargs[user]=${clues[respondentEmail]}
  # --region (create)
  pcargs[region]=None
   # -a (create)
  pcargs[admin]=${clues[respondentEmail]}
  # -o (choose from 'nrec', 'uio', 'uib', 'uit', 'ntnu', 'nmbu', 'vetinst', 'hvl')
  pcargs[org]=None
fi

# --contact (create). If Optional contact was provided, use that instead of respondentEmail.
if [ -z ${clues[optionalContact]} ]
then
  pcargs[contact]=${clues[respondentEmail]}
else
  pcargs[contact]=${clues[optionalContact]}
fi

# -t (choose from 'admin', 'demo', 'personal', 'research', 'education', 'course', 'test', 'hpc', 'vgpu') TODO: add the remaining options
if [[ ${clues[projectType]} == 'Virtual GPU' ]]
then
  pcargs[pctype]=vgpu
elif [[ ${clues[projectCategory]} == 'Admin' ]]
then
  pcargs[pctype]=admin
elif [[ ${clues[projectCategory]} == 'Research' ]]
then
  pcargs[pctype]=research
elif [[ ${clues[projectCategory]} == 'Education' ]]
then
  pcargs[pctype]=education
fi

# --desc
pcargs[desc]="'${clues[projectDescription]}'"

# project (create)
pcargs[project]=${clues[projectName]}

# ---------------------------
#        himlarcli
# ---------------------------

# Parse full project.py cmd
if [[ ${pcargs[createArgument]} == create-private ]]
then
  cmd="./project.py create-private --end ${pcargs[end]} -q ${pcargs[quota]} --rt ${pcargs[rt]} -m ${pcargs[admin]}"
elif [[ ${pcargs[createArgument]} == create ]]
then
  #cmd="./project.py create --region ${pcargs[region]} --end ${pcargs[end]} -a ${pcargs[admin]} -t ${pcargs[pctype]} --desc ${pcargs[desc]} -o ${pcargs[org]} --contact ${pcargs[contact]} -q ${pcargs[quota]} --rt ${pcargs[rt]} -m ${pcargs[project]}"
  cmd="./project.py create --end ${pcargs[end]} -a ${pcargs[admin]} -t ${pcargs[pctype]} --desc ${pcargs[desc]} -o ${pcargs[org]} --contact ${pcargs[contact]} -q ${pcargs[quota]} --rt ${pcargs[rt]} -m ${pcargs[project]}"
fi

echo $cmd

# Build project.py grant cmd -u arguments
if [[ ${pcargs[createArgument]} != create-private ]]
then
  if [ ! -z ${clues[additionalUsers]} ]
  then
    pguserargs=$(bash -c 'users=(${0//\\r\\n/ }); for u in ${users[*]}; do echo -n "-u $u "; done' ${clues[additionalUsers]})
    pguserargs="-u ${pcargs[admin]} $pguserargs"

    # Parse full project.py grant cmd
    cmd="./project.py grant $pguserargs --rt ${pcargs[rt]} -m ${pcargs[project]}"
    echo $cmd
  else
    cmd="./project.py grant -u ${pcargs[admin]} --rt ${pcargs[rt]} -m ${pcargs[project]}"
    echo $cmd
  fi
fi

# Project access grants (choose from 'vgpu', 'shpc', 'shpc_ram', 'shpc_disk1', 'shpc_disk2', 'shpc_disk3', 'shpc_disk4', 'ssd', 'net_uib', 'net_educloud') TODO: add logic for: 'net_uib', 'net_educloud
if [[ ${clues[projectType]} == 'Virtual GPU' ]]
then
  cmd="./project.py access --region ${pcargs[region]} --grant vgpu ${pcargs[project]}"
  echo $cmd
fi
if [ ! -z "${clues[shpcResource]}" ]
then
  # The balanced (shpc.m1a) and CPU-bound (shpc.c1a) flavor sets are included by default with shpc
  cmd="./project.py access --region ${pcargs[region]} --grant shpc ${pcargs[project]}"
  echo $cmd
fi
if [ ! -z "${clues[ssdStorageResource]}" ]
then
  cmd="./project.py access --region ${pcargs[region]} --grant ssd ${pcargs[project]}"
  echo $cmd
fi

# Access to other possible sHPC flavors specified in the form: shpc.r1a, shpc.m1ad1, shpc.m1ad2, shpc.m1ad3, shpc.m1ad4
# .. and required resources: 'shpc_ram', 'shpc_disk1', 'shpc_disk2', 'shpc_disk3', 'shpc_disk4'
# 2024-08-12: To see explanation, you can look on the print from:
# ./project.py access --show-args iaas-team
if [ ${#otherShpcResourcesArray} -gt 0 ]
then
  for ((j=0; j<$numOtherShpcResources; ++j))
  do
    otherShpcResource=${otherShpcResourcesArray[$j]}
    otherShpcResource=${otherShpcResource##*\(}
    otherShpcResource=${otherShpcResource%%\)*}
    # Oppdatering 2024-05-31: Oppfordring fra Trond
    # om at det er lurt å gi tilganger opp til
    # forespurte kapasitet, for shpc_disk*
    # Dermed har brukeren mulighet til å også
    # velge en flavor med mindre kapasitet,
    # dersom det viser seg bedre egnet.
    if [[ $otherShpcResource == 'shpc.r1a' ]]
    then
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_ram ${pcargs[project]}"
      echo $cmd
    elif [[ $otherShpcResource == 'shpc.m1ad1' ]]
    then
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk1 ${pcargs[project]}"
      echo $cmd
    elif [[ $otherShpcResource == 'shpc.m1ad2' ]]
    then
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk1 ${pcargs[project]}"
      echo $cmd
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk2 ${pcargs[project]}"
      echo $cmd
    elif [[ $otherShpcResource == 'shpc.m1ad3' ]]
    then
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk1 ${pcargs[project]}"
      echo $cmd
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk2 ${pcargs[project]}"
      echo $cmd
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk3 ${pcargs[project]}"
      echo $cmd
    elif [[ $otherShpcResource == 'shpc.m1ad4' ]]
    then
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk1 ${pcargs[project]}"
      echo $cmd
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk2 ${pcargs[project]}"
      echo $cmd
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk3 ${pcargs[project]}"
      echo $cmd
      cmd="./project.py access --region ${pcargs[region]} --grant shpc_disk4 ${pcargs[project]}"
      echo $cmd
    fi
    # Oppdatering 2024-05-31: Oppfordring fra Trond:
    # Det er ikke nødvendig å gjøre dette etter bruken av project.py access --grant over
    #cmd="./flavor.py grant --region ${pcargs[region]} $otherShpcResource ${pcargs[project]}"
    #echo $cmd
  done
fi

# ---------------------------
#        openstack cli
# ---------------------------

# Set custom HDD and SSD volume quotas
if [ ! -z ${clues[regularVolumeQuota]} ]
then
  # Parse full openstack HDD quota set cmd
  cmd="openstack quota set --gigabytes ${clues[regularVolumeQuota]} ${pcargs[project]}"
  echo $cmd
fi
if [ ! -z ${clues[ssdVolumeQuota]} ]
  then
  # Parse full openstack SSD quota set cmd
  cmd="openstack quota set --gigabytes $((${clues[regularVolumeQuota]}+${clues[ssdVolumeQuota]})) ${pcargs[project]}" # @caleno verified that this necessary: When setting SSD quota, the regular quota needs to be increased as well with the same amount as the SSD quota.
  echo $cmd
  cmd="openstack quota set --volume-type mass-storage-ssd --gigabytes ${clues[ssdVolumeQuota]} ${pcargs[project]}"
  echo $cmd
fi

# Set increased cores and ram if specified sHPC quota are larger than base quota
if [ ! -z "${clues[projectShpcQuota]}" ]
then
  if [[ ${clues[projectShpcQuota]} == 'Small: 8 CPUs, 32 GB memory' ]]
  then
    shpcCores=8
    shpcRamGB=32
  elif [[ ${clues[projectShpcQuota]} == 'Medium: 16 CPUs, 64 GB memory' ]]
  then
    shpcCores=16
    shpcRamGB=64
  elif [[ ${clues[projectShpcQuota]} == 'Large: 32 CPUs, 128 GB memory' ]]
  then
    shpcCores=32
    shpcRamGB=128
  elif [[ ${clues[projectShpcQuota]} == 'Extra Large: 64 CPUs, 256 GB memory' ]]
  then
    shpcCores=64
    shpcRamGB=256
  elif [[ ${clues[projectShpcQuota]} == 'Big Memory: 64 CPUs, 384 GB memory' ]]
  then
    shpcCores=64
    shpcRamGB=384
  elif [[ ${clues[projectShpcQuota]} == 'Other (specify below)' ]]
  then
    # TODO: Instead read from the Other field (not parsed)
    read -p "shpcCores: " shpcCores
    read -p "shpcRamGB: " shpcRamGB
  fi
  # Increase cores and RAM if necessary
  # Total project quota is the largest of base quota and sHPC quota
  # Cores
  if [ $shpcCores -gt ${pquotas[cores]} ]
  then
    pquotas[cores]=$shpcCores
    cmd="openstack quota set --cores ${pquotas[cores]} ${pcargs[project]}"
    echo $cmd
  fi
  # RAM
  ram=$((1024*$shpcRamGB))
  if [ $ram -gt ${pquotas[ram]} ]
  then
    pquotas[ram]=$ram
    cmd="openstack quota set --ram ${pquotas[ram]} ${pcargs[project]}"
    echo $cmd
  fi
fi
echo
