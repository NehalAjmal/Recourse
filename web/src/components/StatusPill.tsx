interface Props {
  status: string;
}

export default function StatusPill({ status }: Props) {
  let style = "bg-gray-100 text-gray-700";
  let label = "Received";
  
  if (status === 'contest') {
    style = "bg-blue-50 text-blue-700 border border-blue-200";
    label = "Contest";
  } else if (status === 'escalate') {
    style = "bg-amber-50 text-amber-700 border border-amber-200";
    label = "Escalate";
  } else if (status === 'accept') {
    style = "bg-green-50 text-green-700 border border-green-200";
    label = "Accept";
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}
